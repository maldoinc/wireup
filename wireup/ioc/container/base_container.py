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
from wireup.ioc.factory_compiler import FactoryCompiler
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import (
    ContainerObjectIdentifier,
    Qualifier,
)

T = TypeVar("T")
ContainerExitStack = List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]]


class BaseContainer:
    __slots__ = (
        "_compiler",
        "_current_scope_exit_stack",
        "_current_scope_objects",
        "_factories",
        "_global_scope_exit_stack",
        "_global_scope_objects",
        "_override_mgr",
        "_registry",
        "_scoped_compiler",
    )

    def __init__(  # noqa: PLR0913
        self,
        registry: ServiceRegistry,
        override_manager: OverrideManager,
        factory_compiler: FactoryCompiler,
        scoped_compiler: FactoryCompiler,
        global_scope_objects: Dict[ContainerObjectIdentifier, Any],
        global_scope_exit_stack: List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]],
        current_scope_objects: Optional[Dict[ContainerObjectIdentifier, Any]] = None,
        current_scope_exit_stack: Optional[List[Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]]] = None,
    ) -> None:
        self._registry = registry
        self._override_mgr = override_manager
        self._global_scope_objects = global_scope_objects
        self._global_scope_exit_stack = global_scope_exit_stack
        self._current_scope_objects = current_scope_objects
        self._current_scope_exit_stack = current_scope_exit_stack
        self._compiler = factory_compiler
        self._scoped_compiler = scoped_compiler
        self._factories = self._compiler.factories

    @property
    def params(self) -> ParameterBag:
        """Parameter bag associated with this container."""
        return self._registry.parameters

    @property
    def override(self) -> OverrideManager:
        """Override registered container services with new values."""
        return self._override_mgr

    def _synchronous_get(self, klass: Type[T], qualifier: Optional[Qualifier] = None) -> T:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        obj_id = hash(klass if qualifier is None else (klass, qualifier))

        if compiled_factory := self._factories.get(obj_id):
            if compiled_factory.is_async:
                msg = (
                    f"{klass} is an async dependency and it cannot be created in a synchronous context. "
                    "Create and use an async container via wireup.create_async_container."
                )
                raise WireupError(msg)

            return compiled_factory.factory(self)  # type:ignore[no-any-return]

        raise UnknownServiceRequestedError(klass, qualifier)
