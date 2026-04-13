from __future__ import annotations

import inspect
import typing
import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar, Union, cast

from wireup.errors import (
    AsTypeMismatchError,
    CollectionInterfaceUnknownError,
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


_LIFETIME_RANK: dict[InjectableLifetime, int] = {"singleton": 0, "scoped": 1, "transient": 2}


def _loosest_lifetime(lifetimes: list[InjectableLifetime]) -> InjectableLifetime:
    """Return the loosest lifetime among the given impls.

    Loosest = most frequently rebuilt: transient > scoped > singleton. A synthesized collection
    factory inherits its impls' loosest lifetime so existing ``assert_lifetime_valid`` checks
    reject a singleton consumer that depends on a transient-impl collection, identically to how
    they reject singletons depending on plain transient services.
    """
    return max(lifetimes, key=lambda lt: _LIFETIME_RANK[lt])


def _build_set_collection_factory(inner_type: type, impl_count: int) -> Callable[..., Any]:
    """Generate a specialized sync factory that builds a set from its keyword arguments.

    Creates a fresh function object per call so each collection type has a distinct identity
    in ``self.dependencies`` — wireup keys dep maps by function identity. The emitted source
    uses positional parameters and a set literal for the tightest possible bytecode; the
    factory compiler's kwargs loop then emits matching positional-by-name calls.
    """
    param_names = tuple(f"_impl_{i}" for i in range(impl_count))
    params_signature = ", ".join(param_names)
    set_literal = "{" + ", ".join(param_names) + "}" if param_names else "set()"
    source = f"def _collection_factory({params_signature}):\n    return {set_literal}\n"
    namespace: dict[str, Any] = {}
    exec(source, namespace)  # noqa: S102
    factory_fn = cast("Callable[..., Any]", namespace["_collection_factory"])
    factory_fn.__name__ = f"_wireup_set_collection_{inner_type.__name__}"
    factory_fn.__qualname__ = factory_fn.__name__
    return factory_fn


def _build_map_collection_factory(inner_type: type, qualifiers: tuple[Qualifier, ...]) -> Callable[..., Any]:
    """Generate a specialized sync factory that builds a dict keyed by impl qualifiers.

    One parameter per qualified impl, emitted as ``{"qualifier_literal": _impl_i}``. Called
    with the synthesized dep_map parameter names matching the kwargs loop's emission so the
    factory compiler routes each impl's resolved instance to the correct dict slot. Mirrors
    the set-literal shape for the tightest bytecode.
    """
    param_names = tuple(f"_impl_{i}" for i in range(len(qualifiers)))
    params_signature = ", ".join(param_names)
    pairs = ", ".join(f"{q!r}: {name}" for q, name in zip(qualifiers, param_names))
    dict_literal = "{" + pairs + "}" if pairs else "{}"
    source = f"def _collection_factory({params_signature}):\n    return {dict_literal}\n"
    namespace: dict[str, Any] = {}
    exec(source, namespace)  # noqa: S102
    factory_fn = cast("Callable[..., Any]", namespace["_collection_factory"])
    factory_fn.__name__ = f"_wireup_map_collection_{inner_type.__name__}"
    factory_fn.__qualname__ = factory_fn.__name__
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

        self._synthesize_collection_factories()
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

    def _synthesize_collection_factories(self) -> None:
        """Register one ``InjectableFactory`` per collection type referenced by a registered consumer.

        Scans ``self.dependencies`` for parameters rewritten to qualified service deps with a
        ``CollectionKind`` sentinel qualifier (produced by ``param_get_annotation`` for ``Set[T]``
        parameters). For each distinct inner type, generates a specialized factory function via
        ``exec`` whose body is a set literal over its impl-valued keyword arguments, and registers
        it under ``(inner_type, CollectionKind.SET)``. Consumer codegen then resolves the set via
        the standard ``factories[obj_id].factory(container)`` service-branch path — the singleton
        cache swap (factory_compiler.py:222) applies automatically.

        Idempotent: already-synthesized entries are skipped, so repeated ``extend()`` calls don't
        rebuild existing collection factories (matching wireup's compile-once-lock-in semantics
        for every other compiled entity).
        """
        for consumer_factory, deps in list(self.dependencies.items()):
            for param_name, param in deps.items():
                if isinstance(param.qualifier_value, CollectionKind):
                    self._register_collection_factory(
                        inner_type=param.klass,
                        kind=param.qualifier_value,
                        consumer_factory=consumer_factory,
                        param_name=param_name,
                    )

    def ensure_collection_factories_for(self, params: dict[str, AnnotatedParameter], target: Any) -> bool:
        """Synthesize any missing collection factories referenced by an external injection target.

        Used by ``get_valid_injection_annotated_parameters`` for ``@inject_from_container``-decorated
        functions, which aren't in ``self.dependencies`` but may still reference ``Set[T]`` deps.
        Returns ``True`` if any new collection factory was created so the caller can trigger a
        recompile pass.
        """
        created = False
        for param_name, param in params.items():
            if not isinstance(param.qualifier_value, CollectionKind):
                continue
            obj_id = get_container_object_id(param.klass, param.qualifier_value)
            if obj_id in self.factories:
                continue
            self._register_collection_factory(
                inner_type=param.klass,
                kind=param.qualifier_value,
                consumer_factory=target,
                param_name=param_name,
            )
            created = True
        return created

    def _register_collection_factory(
        self,
        *,
        inner_type: type,
        kind: CollectionKind,
        consumer_factory: Any,
        param_name: str,
    ) -> None:
        obj_id = get_container_object_id(inner_type, kind)
        if obj_id in self.factories:
            return

        impl_entries = list(self.iter_impls_for_type(inner_type))
        # Map collections use qualifiers as dict keys, so unqualified impls are excluded
        # — they have nothing to index under. Matches Spring's Map<String, T> semantics.
        if kind is CollectionKind.MAP:
            impl_entries = [entry for entry in impl_entries if entry[0] is not None]
        if not impl_entries:
            raise CollectionInterfaceUnknownError(inner_type, param_name, consumer_factory)

        if kind is CollectionKind.MAP:
            map_qualifiers = tuple(entry[0] for entry in impl_entries)
            factory_fn = _build_map_collection_factory(inner_type, map_qualifiers)
        else:
            factory_fn = _build_set_collection_factory(inner_type, len(impl_entries))

        dep_map: dict[str, AnnotatedParameter] = {}
        impl_lifetimes: list[InjectableLifetime] = []
        for i, (impl_qualifier, impl_obj_id) in enumerate(impl_entries):
            impl_klass = impl_obj_id[0] if isinstance(impl_obj_id, tuple) else impl_obj_id
            annotation = InjectableQualifier(qualifier=impl_qualifier) if impl_qualifier is not None else None
            dep_map[f"_impl_{i}"] = AnnotatedParameter(klass=impl_klass, annotation=annotation)
            impl_lifetimes.append(self.lifetime[impl_obj_id])

        self.dependencies[factory_fn] = dep_map
        self.lifetime[obj_id] = _loosest_lifetime(impl_lifetimes)
        self.factories[obj_id] = InjectableFactory(
            factory=factory_fn,
            callable_type=CallableType.REGULAR,
            is_async=False,
            is_optional_type=False,
            raw_type=inner_type,
        )
        self.impls[inner_type].add(kind)

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
        # Collection sentinel qualifiers bypass interface→impl resolution: the synthesized
        # collection factory is keyed under (klass, CollectionKind.X) directly.
        if isinstance(qualifier, CollectionKind):
            return klass

        if self.is_interface_known(klass):
            return self.interface_resolve_impl(klass, qualifier)

        return klass

    def get_lifetime(self, klass: type, qualifier: Qualifier | None) -> InjectableLifetime:
        return self.lifetime[get_container_object_id(self.get_implementation(klass, qualifier), qualifier)]

    def iter_impls_for_type(self, inner_type: type) -> Iterator[tuple[Qualifier | None, ContainerObjectIdentifier]]:
        """Yield (qualifier, factories_key) for every registered impl of ``inner_type``.

        Spans both registration paths wireup supports today:
          * ``@abstract`` base class + ``@injectable`` concrete subclasses — entries live in
            ``self.interfaces[inner_type]`` keyed ``qualifier -> concrete_class``.
          * ``@injectable(as_type=inner_type)`` and factory functions returning ``inner_type`` —
            entries live in ``self.impls[inner_type]`` as a set of qualifiers; the compiled
            factory is keyed ``(inner_type, qualifier)`` directly.

        The returned ``factories_key`` is usable against ``registry.factories`` and against the
        post-compilation ``FactoryCompiler.factories`` dict in both paths.
        """
        if inner_type in self.interfaces:
            for qualifier, concrete in self.interfaces[inner_type].items():
                yield qualifier, get_container_object_id(concrete, qualifier)
            return

        if inner_type in self.impls:
            for qualifier in self.impls[inner_type]:
                yield qualifier, get_container_object_id(inner_type, qualifier)
