from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar, Union

from wireup.ioc.container_util import ParameterWrapper, ServiceLifetime
from wireup.ioc.util import AnnotatedParameter

if TYPE_CHECKING:
    from wireup import ParameterReference

__T = TypeVar("__T")
AutowireTarget = Union[Callable[..., Any], __T]


class InitializationContext(Generic[__T]):
    """The initialization context for registered targets. A map between an injection target and its dependencies.

    Container uses this to determine what to inject for each target.
    """

    def __init__(self) -> None:
        """Create a new InitializationContext."""
        self.__context: dict[AutowireTarget, dict[str, AnnotatedParameter]] = {}
        self.lifetime: dict[__T, ServiceLifetime] = {}

    def init(self, target: AutowireTarget, lifetime: ServiceLifetime | None) -> bool:
        """Initialize the context for a particular target.

        Returns true on first call. If the target is already registered it returns False.
        """
        if target in self.__context:
            return False

        self.__context[target] = {}

        if isinstance(target, type):
            self.lifetime[target] = lifetime

        return True

    def get(self, target: AutowireTarget) -> dict[str, AnnotatedParameter]:
        """Get the mapping of dependencies to a particular target.

        Raises KeyError if the target does not exist.
        """
        return self.__context[target]

    def put(self, target: AutowireTarget, parameter_name: str, value: AnnotatedParameter) -> None:
        """Update the mapping of dependencies for a particular target.

        Registers a new dependency for the parameter in parameter_name.
        """
        self.__context[target][parameter_name] = value

    def put_param(self, target: AutowireTarget, argument_name: str, parameter_ref: ParameterReference) -> None:
        """Add a parameter to the context.

        :param target: The class type which this parameter belongs to
        :param argument_name: The name of the parameter in the klass initializer.
        :param parameter_ref: A reference to a parameter in the bag.
        """
        self.__context[target][argument_name] = AnnotatedParameter(
            klass=None,
            annotation=ParameterWrapper(parameter_ref),
        )

    def update_params(self, klass: type[__T], params: dict[str, ParameterReference]) -> None:
        """Merge the context information for a particular type.

        Updates the context with the values from the new dictionary. Parameters from the argument will overwrite
        any existing ones with the same name. Behaves the same as the standard dict.update. Parameter values
        will be wrapped in ParameterWrapper.

        :param klass: The class type to be updated
        :param params: A dictionary of parameter references. Keys map to the parameter name and values
        contain references to parameters in the bag.
        """
        self.__context[klass].update(
            {k: AnnotatedParameter(klass=None, annotation=ParameterWrapper(v)) for k, v in params.items()},
        )
