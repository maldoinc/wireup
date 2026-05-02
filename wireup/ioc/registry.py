from __future__ import annotations

import inspect
import typing
import warnings
from collections import defaultdict
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

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
InjectionTarget = AnyCallable | type
"""Represents valid dependency injection targets: Functions and Classes."""


@dataclass
class InjectableFactory:
    factory: Callable[..., Any]
    callable_type: CallableType
    is_async: bool
    is_optional_type: bool
    raw_type: type
    is_synthetic: bool = False


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
        self.impls: dict[type, list[Qualifier | None]] = defaultdict(list)
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
                target_type = target_type | None
            self._register(
                klass=target_type if target_type is not None else klass,
                factory_fn=obj,
                lifetime=impl.lifetime,
                qualifier=impl.qualifier,
                auto_discover_interfaces=impl.as_type is None,
            )

        self._register_sequence_collections()
        self._register_mapping_collections()
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

    @staticmethod
    def _get_collection_lifetime(lifetimes: list[InjectableLifetime]) -> InjectableLifetime:
        for lifetime in ("transient", "scoped"):
            if lifetime in lifetimes:
                return lifetime

        return "singleton"

    def _create_sequence_collection_factory(self, klass: Any, qualifiers: list[Qualifier | None]) -> Callable[..., Any]:
        def _factory(**kwargs: Any) -> Any:
            return tuple(kwargs.values())

        signature_parameters = []
        for idx, qualifier in enumerate(qualifiers):
            annotation = klass if qualifier is None else Annotated[klass, InjectableQualifier(qualifier)]
            signature_parameters.append(
                inspect.Parameter(
                    f"_wireup_item{idx}",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                )
            )

        _factory.__signature__ = inspect.Signature(parameters=signature_parameters)  # type: ignore[attr-defined]
        return _factory

    def _create_mapping_collection_factory(self, klass: Any, qualifiers: list[Qualifier | None]) -> Callable[..., Any]:
        def _factory(**kwargs: Any) -> Any:
            return dict(zip(qualifiers, kwargs.values(), strict=False))

        signature_parameters = []
        for idx, qualifier in enumerate(qualifiers):
            annotation = klass if qualifier is None else Annotated[klass, InjectableQualifier(qualifier)]
            signature_parameters.append(
                inspect.Parameter(
                    f"_wireup_item{idx}",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                )
            )

        _factory.__signature__ = inspect.Signature(parameters=signature_parameters)  # type: ignore[attr-defined]
        return _factory

    def _has_user_defined_sequence_key(self, collection_key: Any) -> bool:
        existing_factory = self.factories.get(get_container_object_id(collection_key, None))
        if existing_factory and not existing_factory.is_synthetic:
            warnings.warn(
                f"Wireup did not register collection injection for {collection_key!r} "
                "because the container already has an explicit registration for that key. "
                "Sequence[T] is reserved for Wireup collection injection. "
                "Migrate it to a NewType or another distinct collection type.",
                FutureWarning,
                stacklevel=4,
            )
            return True

        return False

    def _has_user_defined_mapping_key(self, collection_key: Any) -> bool:
        existing_factory = self.factories.get(get_container_object_id(collection_key, None))
        if existing_factory and not existing_factory.is_synthetic:
            warnings.warn(
                f"Wireup did not register collection injection for {collection_key!r} "
                "because the container already has an explicit registration for that key. "
                "Mapping[Hashable, T] is reserved for Wireup collection injection. "
                "Migrate it to a NewType or another distinct collection type.",
                FutureWarning,
                stacklevel=4,
            )
            return True

        return False

    def _register_sequence_collections(self) -> None:
        for klass, qualifiers in dict(self.impls).items():
            # Only real registration keys should contribute to collection members.
            # Synthetic aliases like raw optional-compat or Sequence[T] keys must not participate here.
            real_qualifiers = [
                qualifier
                for qualifier in qualifiers
                if not self.factories[get_container_object_id(klass, qualifier)].is_synthetic
            ]

            if not real_qualifiers:
                continue

            collection_key = Sequence[klass]  # type:ignore[valid-type]

            if self._has_user_defined_sequence_key(collection_key):
                continue

            existing_factory = self.factories.get(get_container_object_id(collection_key, None))
            if existing_factory and existing_factory.is_synthetic:
                continue

            self._register(
                klass=collection_key,
                factory_fn=self._create_sequence_collection_factory(klass, real_qualifiers),
                lifetime=self._get_collection_lifetime([self.get_lifetime(klass, qual) for qual in real_qualifiers]),
                auto_discover_interfaces=False,
                is_synthetic_factory=True,
            )

    def _register_mapping_collections(self) -> None:
        for klass, qualifiers in dict(self.impls).items():
            # Only real registration keys should contribute to collection members.
            # Synthetic aliases like raw optional-compat or Mapping[Hashable, T] keys must not participate here.
            real_qualifiers = [
                qualifier
                for qualifier in qualifiers
                if not self.factories[get_container_object_id(klass, qualifier)].is_synthetic
            ]

            if not real_qualifiers:
                continue

            collection_key = Mapping[Hashable, klass]  # type:ignore[valid-type]

            if self._has_user_defined_mapping_key(collection_key):
                continue

            existing_factory = self.factories.get(get_container_object_id(collection_key, None))
            if existing_factory and existing_factory.is_synthetic:
                continue

            self._register(
                klass=collection_key,
                factory_fn=self._create_mapping_collection_factory(klass, real_qualifiers),
                lifetime=self._get_collection_lifetime([self.get_lifetime(klass, qual) for qual in real_qualifiers]),
                auto_discover_interfaces=False,
                is_synthetic_factory=True,
            )

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

    def _register(  # noqa: PLR0913
        self,
        klass: type[Any],
        factory_fn: Callable[..., Any],
        lifetime: InjectableLifetime = "singleton",
        qualifier: Qualifier | None = None,
        *,
        auto_discover_interfaces: bool,
        is_synthetic_factory: bool = False,
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
            is_synthetic=is_synthetic_factory,
        )
        self.impls[klass].append(qualifier)

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
                is_synthetic_factory=True,
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
        if self.is_interface_known(klass):
            return self.interface_resolve_impl(klass, qualifier)

        return klass

    def get_lifetime(self, klass: type, qualifier: Qualifier | None) -> InjectableLifetime:
        return self.lifetime[get_container_object_id(self.get_implementation(klass, qualifier), qualifier)]
