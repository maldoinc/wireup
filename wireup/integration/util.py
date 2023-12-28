import inspect
from typing import Any, Callable

from wireup import DependencyContainer
from wireup.ioc.types import InjectableType
from wireup.ioc.util import parameter_get_type_and_annotation


def is_view_using_container(dependency_container: DependencyContainer, view: Callable[..., Any]) -> bool:
    """Determine whether the view is using the given dependency container."""
    for dep in inspect.signature(view).parameters.values():
        param = parameter_get_type_and_annotation(dep)

        is_requesting_injection = isinstance(param.annotation, InjectableType)
        if is_requesting_injection or (param.klass and dependency_container.is_type_known(param.klass)):
            return True

    return False
