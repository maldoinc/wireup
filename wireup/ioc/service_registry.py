from __future__ import annotations

import inspect
import typing
import warnings
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Tuple, TypeVar, Union

from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    InvalidRegistrationTypeError,
    UnknownParameterError,
    UnknownQualifiedServiceRequestedError,
    WireupError,
)
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.types import (
    AnnotatedParameter,
    AnyCallable,
    ContainerObjectIdentifier,
    EmptyContainerInjectionRequest,
    ParameterWrapper,
    ServiceLifetime,
)
from wireup.ioc.util import ensure_is_type, get_globals, param_get_annotation, stringify_type, unwrap_optional_type

if TYPE_CHECKING:
    from wireup._annotations import AbstractDeclaration, ServiceDeclaration
    from wireup.ioc.types import (
        Qualifier,
    )


T = TypeVar("T")
InjectionTarget = Union[AnyCallable, type]
"""Represents valid dependency injection targets: Functions and Classes."""


class FactoryType(Enum):
    REGULAR = auto()
    COROUTINE_FN = auto()
    GENERATOR = auto()
    ASYNC_GENERATOR = auto()


GENERATOR_FACTORY_TYPES = {FactoryType.GENERATOR, FactoryType.ASYNC_GENERATOR}


@dataclass
class ServiceFactory:
    factory: Callable[..., Any]
    factory_type: FactoryType


ServiceCreationDetails = Tuple[Callable[..., Any], ContainerObjectIdentifier, FactoryType, ServiceLifetime]


def _get_factory_type(fn: Callable[..., T]) -> FactoryType:
    """Determine the type of factory based on the function signature."""
    if inspect.iscoroutinefunction(fn):
        return FactoryType.COROUTINE_FN

    if inspect.isgeneratorfunction(fn):
        return FactoryType.GENERATOR

    if inspect.isasyncgenfunction(fn):
        return FactoryType.ASYNC_GENERATOR

    return FactoryType.REGULAR


def _function_get_unwrapped_return_type(fn: Callable[..., T]) -> type[T] | None:
    if isinstance(fn, type):
        return fn

    if ret := fn.__annotations__.get("return"):
        ret = ensure_is_type(ret, globalns=get_globals(fn))
        if not ret:
            return None

        if inspect.isgeneratorfunction(fn) or inspect.isasyncgenfunction(fn):
            args = typing.get_args(ret)
            if not args:
                return None
            ret = args[0]  # Extract the yield type from the generator

        return unwrap_optional_type(ret)  # type: ignore[no-any-return]

    return None


class ServiceRegistry:
    """Container class holding service registration info and dependencies among them."""

    __slots__ = ("ctors", "dependencies", "factories", "impls", "interfaces", "lifetime", "parameters")

    def __init__(
        self,
        parameters: ParameterBag | None = None,
        abstracts: list[AbstractDeclaration] | None = None,
        impls: list[ServiceDeclaration] | None = None,
    ) -> None:
        self.parameters = parameters or ParameterBag()
        self.interfaces: dict[type, dict[Qualifier, type]] = {}
        self.impls: dict[type, set[Qualifier]] = defaultdict(set)
        self.factories: dict[ContainerObjectIdentifier, ServiceFactory] = {}
        self.dependencies: dict[InjectionTarget, dict[str, AnnotatedParameter]] = defaultdict(defaultdict)
        self.lifetime: dict[ContainerObjectIdentifier, ServiceLifetime] = {}
        self.ctors: dict[ContainerObjectIdentifier, ServiceCreationDetails] = {}
        self.extend_with_services(abstracts or [], impls or [])

    def extend_with_services(self, abstracts: list[AbstractDeclaration], impls: list[ServiceDeclaration]) -> None:
        for abstract in abstracts:
            self._register_abstract(abstract.obj)

        for impl in impls:
            self._register(obj=impl.obj, lifetime=impl.lifetime, qualifier=impl.qualifier)

        self.assert_dependencies_valid()
        self._precompute_ctors()

    def _precompute_ctors(self) -> None:
        for interface, impls in self.interfaces.items():
            for qualifier, impl in impls.items():
                factory = self.factories[impl, qualifier]
                self.ctors[interface, qualifier] = (
                    factory.factory,
                    (impl, qualifier),
                    factory.factory_type,
                    self.lifetime[impl, qualifier],
                )

        for impl, qualifiers in self.impls.items():
            for qualifier in qualifiers:
                factory = self.factories[impl, qualifier]
                self.ctors[impl, qualifier] = (
                    factory.factory,
                    (impl, qualifier),
                    factory.factory_type,
                    self.lifetime[impl, qualifier],
                )

    def _register(
        self,
        obj: Callable[..., Any],
        lifetime: ServiceLifetime = "singleton",
        qualifier: Qualifier | None = None,
    ) -> None:
        if not callable(obj):
            raise InvalidRegistrationTypeError(obj)

        klass = _function_get_unwrapped_return_type(obj)

        if klass is None:
            raise FactoryReturnTypeIsEmptyError(obj)

        if self.is_type_with_qualifier_known(klass, qualifier):
            raise DuplicateServiceRegistrationError(klass, qualifier=qualifier)

        def discover_interfaces(bases: tuple[type, ...]) -> None:
            for base in bases:
                if base and self.is_interface_known(base):
                    if qualifier in self.interfaces[base]:
                        raise DuplicateQualifierForInterfaceError(klass, qualifier)

                    self.interfaces[base][qualifier] = klass
                discover_interfaces(base.__bases__)

        if hasattr(klass, "__bases__"):
            discover_interfaces(klass.__bases__)

        self._target_init_context(obj)
        self.lifetime[klass, qualifier] = lifetime
        self.factories[klass, qualifier] = ServiceFactory(
            factory=obj,
            factory_type=_get_factory_type(obj),
        )
        self.impls[klass].add(qualifier)

    def _register_abstract(self, klass: type) -> None:
        self.interfaces[klass] = {}

    def _target_init_context(
        self,
        target: InjectionTarget,
    ) -> None:
        """Init and collect all the necessary dependencies to initialize the specified target."""
        for name, parameter in inspect.signature(target).parameters.items():
            annotated_param = param_get_annotation(parameter, globalns=get_globals(target))

            if not annotated_param:
                msg = f"Wireup dependencies must have types. Please add a type to the '{name}' parameter in {target}."
                raise WireupError(msg)

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

    def assert_dependencies_valid(self) -> None:
        """Assert that all required dependencies exist for this registry instance."""
        for (impl, impl_qualifier), service_factory in self.factories.items():
            for name, dependency in self.dependencies[service_factory.factory].items():
                self.assert_dependency_exists(parameter=dependency, target=impl, name=name)
                self._assert_lifetime_valid(
                    impl=impl,
                    impl_qualifier=impl_qualifier,
                    parameter_name=name,
                    dependency=dependency,
                    factory=service_factory.factory,
                )
                self._assert_valid_resolution_path(dependency=dependency, path=[])

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

        dependency_class = (
            self.interface_resolve_impl(dependency.klass, dependency.qualifier_value)
            if dependency.klass in self.interfaces
            else dependency.klass
        )
        dependency_lifetime = self.lifetime[dependency_class, dependency.qualifier_value]

        if self.lifetime[impl, impl_qualifier] == "singleton" and dependency_lifetime != "singleton":
            msg = (
                f"Parameter '{parameter_name}' of {stringify_type(factory)} "
                f"depends on a service with a '{dependency_lifetime}' lifetime which is not supported. "
                "Singletons can only depend on other singletons."
            )
            raise WireupError(msg)

    def assert_dependency_exists(self, parameter: AnnotatedParameter, target: Any, name: str) -> None:
        """Assert that a dependency exists in the container for the given annotated parameter."""
        if isinstance(parameter.annotation, ParameterWrapper):
            try:
                self.parameters.get(parameter.annotation.param)
            except UnknownParameterError as e:
                msg = (
                    f"Parameter '{name}' of {stringify_type(target)} "
                    f"depends on an unknown Wireup parameter '{e.parameter_name}'"
                    + (
                        ""
                        if isinstance(parameter.annotation.param, str)
                        else f" requested in expression '{parameter.annotation.param.value}'"
                    )
                    + "."
                )
                raise WireupError(msg) from e
        elif not self.is_type_with_qualifier_known(parameter.klass, qualifier=parameter.qualifier_value):
            msg = (
                f"Parameter '{name}' of {stringify_type(target)} "
                f"depends on an unknown service {stringify_type(parameter.klass)} "
                f"with qualifier {parameter.qualifier_value}."
            )
            raise WireupError(msg)

    def _assert_valid_resolution_path(
        self, dependency: AnnotatedParameter, path: list[tuple[AnnotatedParameter, Any]]
    ) -> None:
        """Assert that the resolution path for a dependency does not create a cycle."""
        if dependency.klass in self.interfaces or dependency.is_parameter:
            return
        dependency_service_factory = self.factories[dependency.klass, dependency.qualifier_value]
        if any(p.klass == dependency.klass and p.qualifier_value == dependency.qualifier_value for p, _ in path):

            def stringify_dependency(p: AnnotatedParameter, factory: Any) -> str:
                descriptors = [
                    f'with qualifier "{p.qualifier_value}"' if p.qualifier_value else None,
                    f"created via {factory.factory.__module__}.{factory.factory.__name__}" if factory else None,
                ]
                return (
                    f"{p.klass.__module__}.{p.klass.__name__} ({', '.join([d for d in descriptors if d is not None])})"
                )

            cycle_path = "\n -> ".join(
                f"{stringify_dependency(p, factory)}"
                for p, factory in [*path, (dependency, dependency_service_factory)]
            )
            msg = f"Circular dependency detected for {cycle_path} ! Cycle here"
            raise WireupError(msg)
        for next_dependency in self.dependencies[dependency_service_factory.factory].values():
            self._assert_valid_resolution_path(next_dependency, [*path, (dependency, dependency_service_factory)])
