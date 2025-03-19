from typing import Any, Callable

from wireup.ioc.validation import get_inject_annotated_parameters


def is_callable_using_wireup_dependencies(view: Callable[..., Any]) -> bool:
    return len(get_inject_annotated_parameters(view).keys()) > 0
