from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
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
from wireup.ioc.service_registry import GENERATOR_FACTORY_TYPES, FactoryType, ServiceCreationDetails, ServiceRegistry
from wireup.ioc.types import (
    AnyCallable,
    ContainerObjectIdentifier,
    ContainerScope,
    ParameterWrapper,
    Qualifier,
    ServiceLifetime,
)

T = TypeVar("T")
_ASYNC_FACTORY_TYPES = FactoryType.ASYNC_GENERATOR, FactoryType.COROUTINE_FN
ContainerExitStack = List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]]


class BaseContainer:
    __slots__ = (
        "_current_scope_exit_stack",
        "_current_scope_objects",
        "_global_scope",
        "_override_mgr",
        "_overrides",
        "_params",
        "_registry",
    )

    def __init__(  # noqa: PLR0913
        self,
        registry: ServiceRegistry,
        parameters: ParameterBag,
        override_manager: OverrideManager,
        global_scope: ContainerScope,
        current_scope_objects: Optional[Dict[ContainerObjectIdentifier, Any]] = None,
        current_scope_exit_stack: Optional[List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]]] = None,
    ) -> None:
        self._registry = registry
        self._params = parameters
        self._overrides = override_manager.active_overrides
        self._override_mgr = override_manager
        self._global_scope = global_scope
        self._current_scope_objects = current_scope_objects
        self._current_scope_exit_stack = current_scope_exit_stack

    @property
    def params(self) -> ParameterBag:
        """Parameter bag associated with this container."""
        return self._params

    @property
    def override(self) -> OverrideManager:
        """Override registered container services with new values."""
        return self._override_mgr

    def _try_get_existing_instance(self, obj_id: ContainerObjectIdentifier) -> Any:
        if res := self._overrides.get(obj_id):
            return res

        if obj_id[0] in self._registry.interfaces:
            obj_id = self._registry.interface_resolve_impl(obj_id[0], obj_id[1]), obj_id[1]

        if res := self._global_scope.objects.get(obj_id):
            return res

        if self._current_scope_objects is not None and (res := self._current_scope_objects.get(obj_id)):
            return res

        return None

    async def _async_callable_get_params_to_inject(self, fn: AnyCallable) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        for name, param in self._registry.dependencies[fn].items():
            obj_id = param.obj_id

            if obj := self._try_get_existing_instance(obj_id):
                result[name] = obj
            elif not param.is_parameter:
                result[name] = await self._async_create_instance(self._registry.ctors[obj_id])
            elif param.annotation and isinstance(param.annotation, ParameterWrapper):
                result[name] = self._params.get(param.annotation.param)

        return result

    async def _async_create_instance(self, ctor_details: ServiceCreationDetails) -> Any:
        ctor, resolved_obj_id, factory_type, lifetime = ctor_details
        object_storage, exit_stack = self._get_object_storage_and_exit_stack(lifetime)
        kwargs = await self._async_callable_get_params_to_inject(ctor)
        instance_or_generator = await ctor(**kwargs) if factory_type == FactoryType.COROUTINE_FN else ctor(**kwargs)

        if factory_type in GENERATOR_FACTORY_TYPES:
            exit_stack.append(instance_or_generator)
            instance = (
                next(instance_or_generator)
                if factory_type == FactoryType.GENERATOR
                else await instance_or_generator.__anext__()
            )
        else:
            instance = instance_or_generator

        if object_storage is not None:
            object_storage[resolved_obj_id] = instance

        return instance

    def _create_instance(self, ctor_details: ServiceCreationDetails) -> Any:
        ctor, resolved_obj_id, factory_type, lifetime = ctor_details

        if factory_type in _ASYNC_FACTORY_TYPES:
            msg = (
                f"{resolved_obj_id[0]} is an async dependency and it cannot be created in a synchronous context. "
                "Create and use an async container via wireup.create_async_container. "
            )
            raise WireupError(msg)

        object_storage, exit_stack = self._get_object_storage_and_exit_stack(lifetime)

        instance_or_generator = ctor(**self._callable_get_params_to_inject(ctor))

        if factory_type == FactoryType.GENERATOR:
            exit_stack.append(instance_or_generator)
            instance = next(instance_or_generator)
        else:
            instance = instance_or_generator

        if object_storage is not None:
            object_storage[resolved_obj_id] = instance

        return instance

    _callable_get_params_to_inject = async_to_sync(
        "_callable_get_params_to_inject",
        _async_callable_get_params_to_inject,
        {_async_create_instance: _create_instance},
    )

    def _get_object_storage_and_exit_stack(
        self, lifetime: ServiceLifetime
    ) -> Tuple[Optional[Dict[ContainerObjectIdentifier, Any]], ContainerExitStack]:
        if lifetime == "singleton":
            return self._global_scope.objects, self._global_scope.exit_stack

        if self._current_scope_objects is None or self._current_scope_exit_stack is None:
            msg = (
                "Cannot create 'transient' or 'scoped' lifetime objects from the base container. "
                "Please enter a scope using container.enter_scope. "
                "If you are within a scope, use the scoped container instance to create dependencies."
            )
            raise WireupError(msg)

        return self._current_scope_objects if lifetime == "scoped" else None, self._current_scope_exit_stack

    async def _async_get(self, klass: Type[T], qualifier: Optional[Qualifier] = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        obj_id = klass, qualifier

        if res := self._try_get_existing_instance(obj_id):
            return res  # type: ignore[no-any-return]

        if ctor := self._registry.ctors.get(obj_id):
            return await self._async_create_instance(ctor)  # type: ignore[no-any-return]

        raise UnknownServiceRequestedError(klass, qualifier)

    _synchronous_get = async_to_sync("_synchronous_get", _async_get, {_async_create_instance: _create_instance})
