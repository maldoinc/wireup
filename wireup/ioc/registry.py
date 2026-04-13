from __future__ import annotations

import inspect
import typing
import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar, Union

from wireup.errors import (
    AsTypeMismatchError,
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    InvalidAsTypeError,
    InvalidRegistrationTypeError,
    UnknownQualifiedServiceRequestedError,
)
from wireup.ioc.configuration import ConfigStore
from wireup.ioc.dependency_introspection import injectable_get_dependencies
from wireup.ioc.registry_validation import validate_registry
from wireup.ioc.type_analysis import analyze_type
from wireup.ioc.types import (
    ASYNC_CALLABLE_TYPES,
    AnnotatedParameter,
    AnyCallable,
    CallableType,
    CollectionKind,
    ContainerObjectIdentifier,
    InjectableLifetime,
    InjectableQualifier,
    get_container_object_id,
)
from wireup.ioc.util import ensure_is_type, get_callable_type, get_globals
from wireup.util import stringify_type

if TYPE_CHECKING:
    from wireup._annotations import AbstractDeclaration, InjectableDeclaration
    from wireup.ioc.types import (
        Qualifier,
    )


T = TypeVar("T")
InjectionTarget = Union[AnyCallable, type]
"""Represents valid dependency injection targets: Functions and Classes."""


@dataclass
class InjectableFactory:
    factory: Callable[..., Any]
    callable_type: CallableType
    is_async: bool
    is_optional_type: bool
    raw_type: type


_LIFETIME_RESTRICTIVENESS: dict[InjectableLifetime, int] = {"singleton": 0, "scoped": 1, "transient": 2}


def _tightest_lifetime(lifetimes: list[InjectableLifetime]) -> InjectableLifetime:
    default: InjectableLifetime = "singleton"
    return max(lifetimes, key=lambda lt: _LIFETIME_RESTRICTIVENESS[lt], default=default)


def _build_set_collection_factory(inner_type: type, impl_count: int) -> Callable[..., Any]:
    """Build a fresh sync factory that assembles a set from its keyword impls."""
    param_names = [f"_impl_{i}" for i in range(impl_count)]
    set_literal = "{" + ", ".join(param_names) + "}" if param_names else "set()"
    source = f"def _collection_factory({', '.join(param_names)}):\n    return {set_literal}\n"
    namespace: dict[str, Any] = {}
    exec(source, namespace)  # noqa: S102
    factory_fn: Callable[..., Any] = namespace["_collection_factory"]
    factory_fn.__name__ = factory_fn.__qualname__ = f"_wireup_set_collection_{inner_type.__name__}"
    return factory_fn


def _function_get_unwrapped_return_type(fn: Callable[..., T]) -> type[T] | None:
    if isinstance(fn, type):
        return fn

    if ret := fn.__annotations__.get("return"):
        ret = ensure_is_type(ret, globalns_supplier=lambda: get_globals(fn))
        if not ret:
            return None

        if inspect.isgeneratorfunction(fn) or inspect.isasyncgenfunction(fn):
            args = typing.get_args(ret)
            if not args:
                return None
            ret = args[0]  # Extract the yield type from the generator

        return ret  # type: ignore[no-any-return]

    return None


class ContainerRegistry:
    """Container class holding injectable registration info and dependencies among them."""

    __slots__ = ("dependencies", "factories", "impls", "interfaces", "lifetime", "on_change", "parameters")

    def __init__(
        self,
        config: ConfigStore | None = None,
        abstracts: list[AbstractDeclaration] | None = None,
        impls: list[InjectableDeclaration] | None = None,
    ) -> None:
        self.parameters = config or ConfigStore()
        self.interfaces: dict[type, dict[Qualifier, type]] = {}
        self.impls: dict[type, set[Qualifier]] = defaultdict(set)
        self.factories: dict[ContainerObjectIdentifier, InjectableFactory] = {}
        self.dependencies: dict[InjectionTarget, dict[str, AnnotatedParameter]] = defaultdict(dict)
        self.lifetime: dict[ContainerObjectIdentifier, InjectableLifetime] = {}
        self.on_change: Callable[[], None] | None = None
        self.extend(abstracts=abstracts or [], impls=impls or [])

    def extend(
        self,
        *,
        abstracts: list[AbstractDeclaration] | None = None,
        impls: list[InjectableDeclaration] | None = None,
    ) -> None:
        for abstract in abstracts or []:
            self._register_abstract(abstract.obj)

        for impl in impls or []:
            obj = impl.obj
            if not callable(obj):
                raise InvalidRegistrationTypeError(obj)

            klass = _function_get_unwrapped_return_type(obj)

            if klass is None:
                raise FactoryReturnTypeIsEmptyError(obj)

            type_analysis = analyze_type(klass)

            if impl.as_type is not None:
                self._assert_as_type_compatible(implementation_type=type_analysis.raw_type, as_type=impl.as_type)

            target_type = impl.as_type

            if target_type is not None and type_analysis.is_optional:
                from typing import Optional  # noqa: PLC0415

                target_type = Optional[target_type]

            self._register(
                klass=target_type if target_type is not None else klass,
                factory_fn=obj,
                lifetime=impl.lifetime,
                qualifier=impl.qualifier,
                auto_discover_interfaces=impl.as_type is None,
            )

        self._synthesize_collection_factories_from_dependencies()
        validate_registry(self)
        self._update_factories_async_flag()
        if self.on_change:
            self.on_change()

    @staticmethod
    def _assert_as_type_compatible(implementation_type: Any, as_type: Any) -> None:
        """Try and validate the as_type matches the decorated item on a best-effort basis."""
        if not isinstance(implementation_type, type):
            return

        as_type_analysis = analyze_type(as_type)
        target_type = as_type_analysis.raw_type

        # Raise for anything in as_type=xxx that's not a type.
        if not isinstance(target_type, type):  # type: ignore[reportUnnecessaryIsInstance, unused-ignore]
            raise InvalidAsTypeError(as_type)

        is_protocol = getattr(target_type, "_is_protocol", False)
        is_runtime_protocol = getattr(target_type, "_is_runtime_protocol", False)

        # Protocols are structural. Validate only when runtime-checkable.
        if is_protocol and not is_runtime_protocol:
            return

        try:
            is_compatible = issubclass(implementation_type, target_type)
        except TypeError:
            # Some runtime-checkable protocols are not compatible with issubclass().
            # Skip these failures on a best-effort basis.
            if is_protocol:
                return
            raise

        if not is_compatible:
            raise AsTypeMismatchError(implementation=implementation_type, as_type=target_type)

    def _synthesize_collection_factories_from_dependencies(self) -> None:
        """Sweep registered deps for Set[T] params and synthesize their collection factories."""
        for deps in list(self.dependencies.values()):
            for param in deps.values():
                if isinstance(param.qualifier_value, CollectionKind):
                    self._register_collection_factory(param.klass, param.qualifier_value)

    def register_collection_factories_for(self, params: dict[str, AnnotatedParameter]) -> None:
        """Synthesize any missing Set[T] collection factories and refresh compiled state."""
        created = False
        for param in params.values():
            if isinstance(param.qualifier_value, CollectionKind):
                created |= self._register_collection_factory(param.klass, param.qualifier_value)

        if not created:
            return

        self._update_factories_async_flag()
        if self.on_change:
            self.on_change()

    def _register_collection_factory(self, inner_type: type, kind: CollectionKind) -> bool:
        obj_id = get_container_object_id(inner_type, kind)
        if obj_id in self.factories:
            return False

        impl_entries = list(self._iter_impls_for_type(inner_type))
        factory_fn = _build_set_collection_factory(inner_type, len(impl_entries))

        dep_map: dict[str, AnnotatedParameter] = {}
        impl_lifetimes: list[InjectableLifetime] = []
        for i, (qualifier, concrete) in enumerate(impl_entries):
            annotation = InjectableQualifier(qualifier=qualifier) if qualifier is not None else None
            dep_map[f"_impl_{i}"] = AnnotatedParameter(klass=concrete, annotation=annotation)
            impl_lifetimes.append(self.lifetime[get_container_object_id(concrete, qualifier)])

        self.dependencies[factory_fn] = dep_map
        self.lifetime[obj_id] = _tightest_lifetime(impl_lifetimes)
        self.factories[obj_id] = InjectableFactory(
            factory=factory_fn,
            callable_type=CallableType.REGULAR,
            is_async=False,
            is_optional_type=False,
            raw_type=inner_type,
        )
        self.impls[inner_type].add(kind)
        return True

    def _update_factories_async_flag(self) -> None:
        def _is_dependency_async(impl: type, qualifier: Qualifier | None) -> bool:
            factory = self.factories[get_container_object_id(self.get_implementation(impl, qualifier), qualifier)]

            if factory.is_async:
                return True

            for dep in self.dependencies[factory.factory].values():
                if dep.is_parameter:
                    continue

                if _is_dependency_async(dep.klass, dep.qualifier_value):
                    return True

            return False

        for impl, qualifiers in self.impls.items():
            for qualifier in qualifiers:
                factory = self.factories[get_container_object_id(impl, qualifier)]

                factory.is_async = _is_dependency_async(impl, qualifier)

    def _register(
        self,
        klass: type[Any],
        factory_fn: Callable[..., Any],
        lifetime: InjectableLifetime = "singleton",
        qualifier: Qualifier | None = None,
        *,
        auto_discover_interfaces: bool,
    ) -> None:
        type_analysis = analyze_type(klass)
        klass = type_analysis.normalized_type

        object_id = get_container_object_id(klass, qualifier)
        if self.is_type_with_qualifier_known(klass, qualifier):
            existing_factory = self.factories.get(object_id)
            existing_lifetime = self.lifetime.get(object_id)

            # Idempotent registration: same provider + same metadata can be safely ignored.
            if existing_factory and existing_factory.factory is factory_fn and existing_lifetime == lifetime:
                return

            raise DuplicateServiceRegistrationError(klass, qualifier=qualifier)

        def discover_interfaces(bases: tuple[type, ...]) -> None:
            for base in bases:
                if base and self.is_interface_known(base):
                    if qualifier in self.interfaces[base]:
                        raise DuplicateQualifierForInterfaceError(klass, qualifier)

                    self.interfaces[base][qualifier] = klass
                discover_interfaces(base.__bases__)

        if auto_discover_interfaces and hasattr(klass, "__bases__"):
            discover_interfaces(klass.__bases__)

        self.dependencies[factory_fn] = injectable_get_dependencies(factory_fn)
        self.lifetime[object_id] = lifetime
        callable_type = get_callable_type(factory_fn)
        self.factories[object_id] = InjectableFactory(
            factory=factory_fn,
            callable_type=callable_type,
            is_async=callable_type in ASYNC_CALLABLE_TYPES,
            is_optional_type=type_analysis.is_optional,
            raw_type=type_analysis.raw_type,
        )
        self.impls[klass].add(qualifier)

        if type_analysis.is_optional:
            # Backwards compatibility: In earlier versions when a factory returned T | None
            # you could do container.get(T). Alias that type to the normalized T | None factory.
            # Create a fake factory that warns and returns the original instance.
            # https://github.com/maldoinc/wireup/commit/00590dc741035a4c7042c5b6fc434ed08e27f5c0
            def compat_fn(raw_type_instance: Any) -> Any:
                type_name = type_analysis.raw_type.__name__
                deprecated_msg = (
                    f"Deprecated: {stringify_type(type_analysis.raw_type)} was registered as optional "
                    f"and retrieving it via container.get({type_name}) is deprecated. "
                    f"Please use container.get({type_name} | None) or container.get(Optional[{type_name}]) instead."
                )

                warnings.warn(deprecated_msg, DeprecationWarning, stacklevel=4)

                return raw_type_instance

            compat_fn.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
                parameters=[
                    inspect.Parameter(
                        "raw_type_instance",
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=klass,
                    )
                ],
            )

            self._register(
                type_analysis.raw_type,
                factory_fn=compat_fn,
                lifetime=lifetime,
                qualifier=qualifier,
                auto_discover_interfaces=True,
            )

    def _register_abstract(self, klass: type) -> None:
        self.interfaces[klass] = {}

    def is_impl_with_qualifier_known(self, klass: type, qualifier_value: Qualifier | None) -> bool:
        """Determine if klass representing a concrete implementation + qualifier is known by the registry."""
        return klass in self.impls and qualifier_value in self.impls[klass]

    def is_type_with_qualifier_known(self, klass: type, qualifier: Qualifier | None) -> bool:
        """Determine if klass+qualifier is known. Klass can be a concrete class or one registered as abstract."""
        is_known_impl = self.is_impl_with_qualifier_known(klass, qualifier)
        is_known_intf = self.__is_interface_with_qualifier_known(klass, qualifier)

        return is_known_impl or is_known_intf

    def __is_interface_with_qualifier_known(
        self,
        klass: type,
        qualifier: Qualifier | None,
    ) -> bool:
        return klass in self.interfaces and qualifier in self.interfaces[klass]

    def is_interface_known(self, klass: type) -> bool:
        return klass in self.interfaces

    def interface_resolve_impl(self, klass: type, qualifier: Qualifier | None) -> type:
        """Given an interface and qualifier return the concrete implementation."""
        impls = self.interfaces.get(klass, {})

        if qualifier in impls:
            return impls[qualifier]

        raise UnknownQualifiedServiceRequestedError(klass, qualifier, set(impls.keys()))

    def get_implementation(self, klass: type, qualifier: Qualifier | None) -> type:
        """Return the concrete implementation for a given class/interface and qualifier."""
        if isinstance(qualifier, CollectionKind):
            return klass

        if self.is_interface_known(klass):
            return self.interface_resolve_impl(klass, qualifier)

        return klass

    def get_lifetime(self, klass: type, qualifier: Qualifier | None) -> InjectableLifetime:
        return self.lifetime[get_container_object_id(self.get_implementation(klass, qualifier), qualifier)]

    def _iter_impls_for_type(self, inner_type: type) -> Iterator[tuple[Qualifier | None, type]]:
        """Yield (qualifier, concrete_class) for every registered impl of ``inner_type``."""
        seen: set[Qualifier | None] = set()

        for qualifier, concrete in self.interfaces.get(inner_type, {}).items():
            seen.add(qualifier)
            yield qualifier, concrete

        for qualifier in self.impls.get(inner_type, ()):
            if not isinstance(qualifier, CollectionKind) and qualifier not in seen:
                yield qualifier, inner_type
