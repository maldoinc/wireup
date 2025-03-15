import inspect
from typing import Any, Callable

from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.util import get_globals, param_get_annotation


def is_view_using_container(dependency_container: BaseContainer, view: Callable[..., Any]) -> bool:
    """Determine whether the view is using the given dependency container."""
    for dep in inspect.signature(view).parameters.values():
        if param := param_get_annotation(dep, globalns=get_globals(view)):
            is_known_type = param.klass and dependency_container.is_type_known(param.klass)

            if param.annotation or is_known_type:
                return True

    return False
