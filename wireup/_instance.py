from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

from wireup._annotations import injectable

if TYPE_CHECKING:
    from wireup.ioc.types import Qualifier

T = TypeVar("T")


def instance(
    obj: T,
    *,
    as_type: type[Any],
    qualifier: Qualifier | None = None,
) -> Callable[[], T]:
    """
    Register an existing instance with the container.

    :param obj: The instance to register.
    :param as_type: The type to expose to the container. Must be provided.
    :param qualifier: An optional qualifier for the instance.
    """

    @injectable(qualifier=qualifier, as_type=as_type)
    def _instance_provider() -> T:
        return obj

    return _instance_provider
