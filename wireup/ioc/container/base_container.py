import logging
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from wireup._async_to_sync import async_to_sync
from wireup.errors import (
    UnknownServiceRequestedError,
    WireupError,
)
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import GENERATOR_FACTORY_TYPES, FactoryType, ServiceRegistry
from wireup.ioc.types import (
    AnyCallable,
    ContainerObjectIdentifier,
    ContainerScope,
    ParameterWrapper,
    Qualifier,
    ServiceLifetime,
)

T = TypeVar("T")
logger = logging.getLogger(__name__)
_ASYNC_FACTORY_TYPES = FactoryType.ASYNC_GENERATOR, FactoryType.COROUTINE_FN
ContainerExitStack = List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]]


class BaseContainer:
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
        overrides: Dict[ContainerObjectIdentifier, Any],
        global_scope: ContainerScope,
        current_scope: Optional[ContainerScope] = None,
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

    @property
    def override(self) -> OverrideManager:
        """Override registered container services with new values."""
        return self._override_mgr

    def _try_get_existing_instance(self, klass: Type[T], qualifier: Qualifier) -> Optional[T]:
        obj_id = klass, qualifier

        if res := self._overrides.get(obj_id):
            return res  # type: ignore[no-any-return]

        if self._registry.is_interface_known(klass):
            resolved_type: type = self._registry.interface_resolve_impl(klass, qualifier)
            obj_id = resolved_type, qualifier

        if res := self._global_scope.objects.get(obj_id):
            return res  # type: ignore[no-any-return]

        if self._current_scope is not None and (res := self._current_scope.objects.get(obj_id)):
            return res  # type: ignore[no-any-return]

        return None

    async def _async_callable_get_params_to_inject(
        self,
        fn: AnyCallable,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        for name, param in self._registry.dependencies[fn].items():
            if obj := self._try_get_existing_instance(param.klass, param.qualifier_value):
                result[name] = obj
            elif param.klass and (instance := await self._async_create_instance(param.klass, param.qualifier_value)):
                result[name] = instance
            elif param.annotation and isinstance(param.annotation, ParameterWrapper):
                result[name] = self._params.get(param.annotation.param)

        return result

    async def _async_create_instance(self, klass: Type[T], qualifier: Optional[Qualifier]) -> Optional[T]:
        ctor_and_type = self._registry.ctors.get((klass, qualifier))

        if not ctor_and_type:
            return None

        ctor, resolved_type, factory_type = ctor_and_type
        lifetime = self._registry.lifetime[resolved_type]
        scope = self._get_scope(lifetime)
        kwargs = await self._async_callable_get_params_to_inject(ctor)
        instance_or_generator = await ctor(**kwargs) if factory_type == FactoryType.COROUTINE_FN else ctor(**kwargs)

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

        return self._wrap_result(  # type: ignore[no-any-return]
            scope=scope,
            generator=generator,
            lifetime=lifetime,
            instance=instance,
            object_identifier=(resolved_type, qualifier),
        )

    def _create_instance(self, klass: Type[T], qualifier: Optional[Qualifier]) -> Optional[T]:
        ctor_and_type = self._registry.ctors.get((klass, qualifier))

        if not ctor_and_type:
            return None

        ctor, resolved_type, factory_type = ctor_and_type

        if factory_type in _ASYNC_FACTORY_TYPES:
            msg = (
                f"{klass} is an async dependency and it cannot be created in a synchronous context. "
                "Create and use an async container via wireup.create_async_container. "
            )
            raise WireupError(msg)

        lifetime = self._registry.lifetime[resolved_type]
        scope = self._get_scope(lifetime)

        instance_or_generator = ctor(**self._callable_get_params_to_inject(ctor))

        if factory_type == FactoryType.GENERATOR:
            generator = instance_or_generator
            instance = next(instance_or_generator)
        else:
            instance = instance_or_generator
            generator = None

        return self._wrap_result(  # type: ignore[no-any-return]
            scope=scope,
            lifetime=lifetime,
            generator=generator,
            instance=instance,
            object_identifier=(resolved_type, qualifier),
        )

    _callable_get_params_to_inject = async_to_sync(
        "_callable_get_params_to_inject",
        _async_callable_get_params_to_inject,
        {_async_create_instance: _create_instance},
    )

    def _wrap_result(
        self,
        *,
        lifetime: ServiceLifetime,
        scope: ContainerScope,
        generator: Optional[Any],
        instance: T,
        object_identifier: ContainerObjectIdentifier,
    ) -> T:
        if lifetime != "transient":
            scope.objects[object_identifier] = instance

        if generator:
            scope.exit_stack.append(generator)

        return instance

    def _get_scope(self, lifetime: ServiceLifetime) -> ContainerScope:
        if lifetime == "singleton":
            return self._global_scope

        if self._current_scope is None:
            msg = (
                "Cannot create 'transient' or 'scoped' lifetime objects from the base container. "
                "Please enter a scope using container.enter_scope. "
                "If you are within a scope, use the scoped container instance to create dependencies."
            )
            raise WireupError(msg)

        return self._current_scope

    async def _async_get(self, klass: Type[T], qualifier: Optional[Qualifier] = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """

        if res := self._try_get_existing_instance(klass, qualifier):
            return res

        if res := await self._async_create_instance(klass, qualifier):
            return res

        raise UnknownServiceRequestedError(klass)

    _synchronous_get = async_to_sync("_synchronous_get", _async_get, {_async_create_instance: _create_instance})
