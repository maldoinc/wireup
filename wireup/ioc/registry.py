from __future__ import annotations

import inspect
import typing
import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union

from wireup.errors import (
    AsTypeMismatchError,
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    InvalidAsTypeError,
    InvalidRegistrationTypeError,
    PositionalOnlyParameterError,
    UnknownParameterError,
    UnknownQualifiedServiceRequestedError,
    WireupError,
)
from wireup.ioc.configuration import ConfigStore
from wireup.ioc.type_analysis import analyze_type
from wireup.ioc.types import (
    ASYNC_CALLABLE_TYPES,
    AnnotatedParameter,
    AnyCallable,
    CallableType,
    ConfigInjectionRequest,
    ContainerObjectIdentifier,
    EmptyContainerInjectionRequest,
    InjectableLifetime,
)
from wireup.ioc.util import ensure_is_type, get_callable_type, get_globals, param_get_annotation
from wireup.util import format_name, stringify_type

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

    __slots__ = ("dependencies", "factories", "impls", "interfaces", "lifetime", "parameters")

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
        self.dependencies: dict[InjectionTarget, dict[str, AnnotatedParameter]] = defaultdict(defaultdict)
        self.lifetime: dict[ContainerObjectIdentifier, InjectableLifetime] = {}
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

            if impl.as_type:
                self._assert_as_type_compatible(implementation_type=type_analysis.raw_type, as_type=impl.as_type)

            target_type = impl.as_type

            if target_type and type_analysis.is_optional:
                from typing import Optional  # noqa: PLC0415

                target_type = Optional[target_type]

            self._register(
                klass=target_type or klass,
                factory_fn=obj,
                lifetime=impl.lifetime,
                qualifier=impl.qualifier,
                auto_discover_interfaces=impl.as_type is None,
            )

        self.assert_dependencies_valid()
        self._update_factories_async_flag()

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

    def _update_factories_async_flag(self) -> None:
        def _is_dependency_async(impl: type, qualifier: Qualifier) -> bool:
            factory = self.factories[self.get_implementation(impl, qualifier), qualifier]

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
                factory = self.factories[impl, qualifier]

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

        if self.is_type_with_qualifier_known(klass, qualifier):
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

        self._target_init_context(factory_fn)
        self.lifetime[klass, qualifier] = lifetime
        callable_type = get_callable_type(factory_fn)
        self.factories[klass, qualifier] = InjectableFactory(
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

    def _target_init_context(
        self,
        target: InjectionTarget,
    ) -> None:
        """Init and collect all the necessary dependencies to initialize the specified target."""
        for name, parameter in inspect.signature(target).parameters.items():
            if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
                continue

            annotated_param = param_get_annotation(parameter, globalns_supplier=lambda: get_globals(target))

            if not annotated_param:
                if parameter.default is not inspect.Parameter.empty:
                    continue

                msg = f"Wireup dependencies must have types. Please add a type to the '{name}' parameter in {target}."
                raise WireupError(msg)

            if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                raise PositionalOnlyParameterError(name, target)

            if isinstance(annotated_param.annotation, EmptyContainerInjectionRequest):
                warnings.warn(
                    f"Redundant Injected[T] or Annotated[T, Inject()] in parameter '{name}' of "
                    f"{stringify_type(target)}. See: "
                    "https://maldoinc.github.io/wireup/latest/annotations/",
                    stacklevel=2,
                )

            self.dependencies[target][name] = annotated_param

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
        return self.lifetime[self.get_implementation(klass, qualifier), qualifier]

    def assert_dependencies_valid(self) -> None:
        """Assert that all required dependencies exist for this registry instance."""
        for (impl, impl_qualifier), injectable_factory in self.factories.items():
            unknown_dependencies_with_default: list[str] = []

            for name, dependency in self.dependencies[injectable_factory.factory].items():
                try:
                    self.assert_dependency_exists(parameter=dependency, target=impl, name=name)
                except WireupError:
                    if dependency.has_default_value:
                        unknown_dependencies_with_default.append(name)
                        continue

                    raise

                self._assert_lifetime_valid(
                    impl=impl,
                    impl_qualifier=impl_qualifier,
                    parameter_name=name,
                    dependency=dependency,
                    factory=injectable_factory.factory,
                )
                self._assert_valid_resolution_path(dependency=dependency, path=[])

            for name in unknown_dependencies_with_default:
                del self.dependencies[injectable_factory.factory][name]

    def _assert_lifetime_valid(
        self,
        *,
        impl: Any,
        impl_qualifier: Qualifier | None,
        parameter_name: str,
        dependency: AnnotatedParameter,
        factory: AnyCallable,
    ) -> None:
        if dependency.is_parameter:
            return

        dependency_lifetime = self.get_lifetime(dependency.klass, dependency.qualifier_value)

        if self.lifetime[impl, impl_qualifier] == "singleton" and dependency_lifetime != "singleton":
            msg = (
                f"Parameter '{parameter_name}' of {stringify_type(factory)} "
                f"depends on an injectable with a '{dependency_lifetime}' lifetime which is not supported. "
                "Singletons can only depend on other singletons."
            )
            raise WireupError(msg)

    def assert_dependency_exists(self, parameter: AnnotatedParameter, target: Any, name: str) -> None:
        """Assert that a dependency exists in the container for the given annotated parameter."""
        if isinstance(parameter.annotation, ConfigInjectionRequest):
            try:
                self.parameters.get(parameter.annotation.config_key)
            except UnknownParameterError as e:
                msg = (
                    f"Parameter '{name}' of {stringify_type(target)} "
                    f"depends on an unknown Wireup config key '{e.parameter_name}'"
                    + (
                        ""
                        if isinstance(parameter.annotation.config_key, str)
                        else f" requested in expression '{parameter.annotation.config_key.value}'"
                    )
                    + "."
                )
                raise WireupError(msg) from e
        elif not self.is_type_with_qualifier_known(parameter.klass, qualifier=parameter.qualifier_value):
            type_str = format_name(analyze_type(parameter.klass).raw_type, parameter.qualifier_value)
            msg = f"Parameter '{name}' of {stringify_type(target)} has an unknown dependency on {type_str}."
            raise WireupError(msg)

    def _assert_valid_resolution_path(
        self, dependency: AnnotatedParameter, path: list[tuple[AnnotatedParameter, Any]]
    ) -> None:
        """Assert that the resolution path for a dependency does not create a cycle."""
        if dependency.klass in self.interfaces or dependency.is_parameter:
            return
        dependency_injectable_factory = self.factories[dependency.klass, dependency.qualifier_value]
        new_path: list[tuple[AnnotatedParameter, Any]] = [*path, (dependency, dependency_injectable_factory)]

        if any(p.klass == dependency.klass and p.qualifier_value == dependency.qualifier_value for p, _ in path):

            def stringify_dependency(p: AnnotatedParameter, factory: Any) -> str:
                descriptors = [
                    f"created via {factory.factory.__module__}.{factory.factory.__name__}" if factory else None,
                ]
                qualifier_desc = ", ".join([d for d in descriptors if d is not None])
                qualifier_desc = f" ({qualifier_desc})" if qualifier_desc else ""

                return f"{format_name(p.klass, p.qualifier_value)}{qualifier_desc}"

            cycle_path = "\n -> ".join(f"{stringify_dependency(p, factory)}" for p, factory in new_path)
            msg = f"Circular dependency detected for {cycle_path} ! Cycle here"
            raise WireupError(msg)

        for next_dependency in self.dependencies[dependency_injectable_factory.factory].values():
            self._assert_valid_resolution_path(next_dependency, path=new_path)
