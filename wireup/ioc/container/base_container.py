from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from wireup.errors import (
    UnknownQualifiedServiceRequestedError,
    UnknownServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
    WireupError,
)
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.service_registry import GENERATOR_FACTORY_TYPES, FactoryType
from wireup.ioc.types import (
    AnnotatedParameter,
    AnyCallable,
    ContainerScope,
    CreationResult,
    EmptyContainerInjectionRequest,
    InjectionResult,
    ParameterWrapper,
    Qualifier,
    ServiceLifetime,
    ServiceQualifier,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import AsyncGeneratorType, GeneratorType

    from wireup import ParameterBag
    from wireup.ioc.service_registry import ServiceRegistry
    from wireup.ioc.types import ContainerObjectIdentifier, Qualifier

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BaseContainer:
    """Base Container class providing core functionality."""

    __slots__ = (
        "_current_scope",
        "_global_scope",
        "_override_mgr",
        "_overrides",
        "_params",
        "_registry",
    )

    def __init__(
        self,
        registry: ServiceRegistry,
        parameters: ParameterBag,
        overrides: dict[ContainerObjectIdentifier, Any],
        global_scope: ContainerScope,
        current_scope: ContainerScope | None = None,
    ) -> None:
        self._registry = registry
        self._params = parameters
        self._overrides = overrides
        self._override_mgr = OverrideManager(overrides, self._registry.is_type_with_qualifier_known)
        self._global_scope = global_scope
        self._current_scope = current_scope

    @property
    def params(self) -> ParameterBag:
        """Parameter bag associated with this container."""
        return self._params

    def is_type_known(self, klass: type) -> bool:
        """Given a class type return True if's registered in the container as a service or interface."""
        return klass in self._registry.impls or klass in self._registry.interfaces

    @property
    def override(self) -> OverrideManager:
        """Override registered container services with new values."""
        return self._override_mgr

    def _get_ctor(
        self, klass: type[T], qualifier: Qualifier | None
    ) -> tuple[Callable[..., Any], type[T], FactoryType] | None:
        if self._registry.is_interface_known(klass):
            klass = self._registry.interface_resolve_impl(klass, qualifier)

        if ctor := self._registry.factories.get((klass, qualifier)):
            return ctor.factory, klass, ctor.factory_type

        # Raise if the current impl is known but not necessarily with this qualifier.
        if klass in self._registry.impls:
            if not self._registry.is_impl_with_qualifier_known(klass, qualifier):
                raise UnknownQualifiedServiceRequestedError(
                    klass,
                    qualifier,
                    self._registry.impls[klass],
                )

            return klass, klass, FactoryType.REGULAR

        # Throw if a qualifier is being used on an unknown type.
        if qualifier:
            raise UsageOfQualifierOnUnknownObjectError(qualifier)

        return None

    def _try_get_existing_value(self, param: AnnotatedParameter) -> tuple[Any, bool]:
        if param.klass:
            obj_id = param.klass, param.qualifier_value

            if res := self._overrides.get(obj_id):
                return res, True

            if self._registry.is_interface_known(param.klass):
                resolved_type = self._registry.interface_resolve_impl(param.klass, param.qualifier_value)
                obj_id = resolved_type, param.qualifier_value

            if res := self._global_scope.objects.get(obj_id):
                return res, True

            if self._current_scope is not None and (res := self._current_scope.objects.get(obj_id)):
                return res, True

        if isinstance(param.annotation, ParameterWrapper):
            return self._params.get(param.annotation.param), True

        return None, False

    def _callable_get_params_to_inject(self, fn: AnyCallable) -> InjectionResult:
        result: dict[str, Any] = {}
        names_to_remove: set[str] = set()
        exit_stack: list[GeneratorType[Any, Any, Any] | AsyncGeneratorType[Any, Any]] = []

        for name, param in self._registry.context.dependencies[fn].items():
            obj, value_found = self._try_get_existing_value(param)

            if value_found:
                result[name] = obj
            elif param.klass and (creation := self._create_instance(param.klass, param.qualifier_value)):
                if creation.exit_stack:
                    exit_stack.extend(creation.exit_stack)
                result[name] = creation.instance
            else:
                # Normally the container won't throw if it encounters a type it doesn't know about
                # But if it's explicitly marked as to be injected then we need to throw.
                if param.klass and isinstance(param.annotation, EmptyContainerInjectionRequest):
                    raise UnknownServiceRequestedError(param.klass)

                names_to_remove.add(name)

        # If the container is creating services, it is assumed to be final, so unnecessary entries can be removed
        # from the context in order to speed up subsequent calls.
        if names_to_remove:
            self._registry.context.remove_dependencies(fn, names_to_remove)

        return InjectionResult(kwargs=result, exit_stack=exit_stack)

    async def _async_callable_get_params_to_inject(self, fn: AnyCallable) -> InjectionResult:
        result: dict[str, Any] = {}
        names_to_remove: set[str] = set()
        exit_stack: list[GeneratorType[Any, Any, Any] | AsyncGeneratorType[Any, Any]] = []

        for name, param in self._registry.context.dependencies[fn].items():
            obj, value_found = self._try_get_existing_value(param)

            if value_found:
                result[name] = obj
            elif param.klass and (creation := await self._async_create_instance(param.klass, param.qualifier_value)):
                if creation.exit_stack:
                    exit_stack.extend(creation.exit_stack)
                result[name] = creation.instance
            else:
                # Normally the container won't throw if it encounters a type it doesn't know about
                # But if it's explicitly marked as to be injected then we need to throw.
                if param.klass and isinstance(param.annotation, EmptyContainerInjectionRequest):
                    raise UnknownServiceRequestedError(param.klass)

                names_to_remove.add(name)

        # If the container is creating services, it is assumed to be final, so unnecessary entries can be removed
        # from the context in order to speed up subsequent calls.
        if names_to_remove:
            self._registry.context.remove_dependencies(fn, names_to_remove)

        return InjectionResult(kwargs=result, exit_stack=exit_stack)

    def _create_instance(self, klass: type[T], qualifier: Qualifier | None) -> CreationResult | None:
        ctor_and_type = self._get_ctor(klass=klass, qualifier=qualifier)

        if not ctor_and_type:
            return None

        ctor, resolved_type, factory_type = ctor_and_type

        if factory_type in {FactoryType.ASYNC_GENERATOR, FactoryType.COROUTINE_FN}:
            msg = (
                f"{klass} is an async dependency and it cannot be created in a blocking context. "
                f"You likely used `container.get({klass.__module__}.{klass.__name__})` or called `get` on a dependent. "
                "Use `await container.aget` instead of `container.get`."
            )
            raise WireupError(msg)

        lifetime = self._registry.context.lifetime[resolved_type]
        self._assert_lifetime_is_valid(lifetime)

        injection_result = self._callable_get_params_to_inject(ctor)
        instance_or_generator = ctor(**injection_result.kwargs)

        if factory_type == FactoryType.GENERATOR:
            generator = instance_or_generator
            instance = next(instance_or_generator)
        else:
            instance = instance_or_generator
            generator = None

        return self._wrap_result(
            lifetime=lifetime,
            generator=generator,
            instance=instance,
            object_identifier=(resolved_type, qualifier),
            injection_result=injection_result,
        )

    async def _async_create_instance(self, klass: type[T], qualifier: Qualifier | None) -> CreationResult | None:
        ctor_and_type = self._get_ctor(klass=klass, qualifier=qualifier)

        if not ctor_and_type:
            return None

        ctor, resolved_type, factory_type = ctor_and_type
        lifetime = self._registry.context.lifetime[resolved_type]
        self._assert_lifetime_is_valid(lifetime)
        injection_result = await self._async_callable_get_params_to_inject(ctor)
        instance_or_generator = (
            await ctor(**injection_result.kwargs)
            if factory_type == FactoryType.COROUTINE_FN
            else ctor(**injection_result.kwargs)
        )

        if factory_type in GENERATOR_FACTORY_TYPES:
            generator = instance_or_generator
            instance = (
                next(instance_or_generator)
                if factory_type == FactoryType.GENERATOR
                else await instance_or_generator.__anext__()
            )
        else:
            generator = None
            instance = instance_or_generator

        return self._wrap_result(
            lifetime=lifetime,
            generator=generator,
            instance=instance,
            object_identifier=(resolved_type, qualifier),
            injection_result=injection_result,
        )

    def _wrap_result(
        self,
        *,
        lifetime: ServiceLifetime,
        generator: Any | None,
        instance: Any,
        object_identifier: ContainerObjectIdentifier,
        injection_result: InjectionResult,
    ) -> CreationResult:
        is_singleton = lifetime == ServiceLifetime.SINGLETON

        if is_singleton:
            self._global_scope.objects[object_identifier] = instance
        elif self._current_scope is not None and lifetime == ServiceLifetime.SCOPED:
            self._current_scope.objects[object_identifier] = instance

        if generator:
            result_exit_stack = injection_result.exit_stack
            if is_singleton:
                self._global_scope.exit_stack.append(generator)
                result_exit_stack = []
            elif self._current_scope is not None:
                self._current_scope.exit_stack.append(generator)
                result_exit_stack = []
            else:
                result_exit_stack.append(generator)

            return CreationResult(instance=instance, exit_stack=result_exit_stack)

        return CreationResult(instance=instance, exit_stack=injection_result.exit_stack)

    def _assert_lifetime_is_valid(self, lifetime: ServiceLifetime) -> None:
        if lifetime is not ServiceLifetime.SINGLETON and self._current_scope is None:
            msg = (
                "Creating transient or scoped objects from the base container is deprecated. "
                "Please enter a scope using wireup.enter_scope or wireup.enter_async_scope."
            )
            logger.warning(msg)

    def _synchronous_get(self, klass: type[T], qualifier: Qualifier | None = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        res, found = self._try_get_existing_value(
            AnnotatedParameter(klass=klass, annotation=ServiceQualifier(qualifier))
        )

        if found:
            return res  # type: ignore[no-any-return]

        if res := self._create_instance(klass, qualifier):
            if res.exit_stack:
                msg = "Container.get does not support Transient lifetime service generator factories."
                raise WireupError(msg)

            return res.instance  # type: ignore[no-any-return]

        raise UnknownServiceRequestedError(klass)

    async def _async_get(self, klass: type[T], qualifier: Qualifier | None = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        if res := self._overrides.get((klass, qualifier)):
            return res  # type: ignore[no-any-return]

        if self._registry.is_interface_known(klass):
            klass = self._registry.interface_resolve_impl(klass, qualifier)

        if instance := self._global_scope.objects.get((klass, qualifier)):
            return instance  # type: ignore[no-any-return]

        if res := await self._async_create_instance(klass, qualifier):
            if res.exit_stack:
                msg = "Container.get does not support Transient lifetime service generator factories."
                raise WireupError(msg)

            return res.instance  # type: ignore[no-any-return]

        raise UnknownServiceRequestedError(klass)
