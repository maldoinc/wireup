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

from wireup.errors import (
    UnknownServiceRequestedError,
    WireupError,
)
from wireup.ioc.container.compiler import FactoryCompiler
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import (
    ContainerObjectIdentifier,
    ContainerScope,
    Qualifier,
)

T = TypeVar("T")
ContainerExitStack = List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]]


class BaseContainer:
    __slots__ = (
        "_compiler",
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
        factory_compiler: FactoryCompiler,
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
        self._compiler = factory_compiler

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

    async def _async_get(self, klass: Type[T], qualifier: Optional[Qualifier] = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        obj_id = klass, qualifier

        if res := self._try_get_existing_instance(obj_id):
            return res  # type:ignore[no-any-return]

        if compiled_factory := self._compiler.factories.get(obj_id):
            res = compiled_factory.factory(self)

            return await res if compiled_factory.is_async else res  # type:ignore[no-any-return]

        raise UnknownServiceRequestedError(klass, qualifier)

    def _synchronous_get(self, klass: Type[T], qualifier: Optional[Qualifier] = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        obj_id = klass, qualifier

        if res := self._try_get_existing_instance(obj_id):
            return res  # type:ignore[no-any-return]

        if compiled_factory := self._compiler.factories.get(obj_id):
            if compiled_factory.is_async:
                msg = (
                    f"{klass} is an async dependency and it cannot be created in a synchronous context. "
                    "Create and use an async container via wireup.create_async_container."
                )
                raise WireupError(msg)

            return compiled_factory.factory(self)  # type:ignore[no-any-return]

        raise UnknownServiceRequestedError(klass, qualifier)
