from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

from wireup._annotations import InjectableDeclaration

if TYPE_CHECKING:
    from wireup.ioc.types import Qualifier

T = TypeVar("T")


def instance(
    obj: T,
    as_type: type[Any] | None = None,
    qualifier: Qualifier | None = None,
) -> Callable[[], T]:
    """
    Register an existing instance with the container.

    :param obj: The instance to register.
    :param as_type: The type to expose to the container. Must be provided.
    :param qualifier: An optional qualifier for the instance.
    """
    if as_type is None:
        msg = "Argument 'as_type' is required when registering an instance."
        raise ValueError(msg)

    def _instance_provider() -> T:
        return obj

    # The container requires a return type annotation to determine what is being provided.
    _instance_provider.__annotations__["return"] = as_type

    _instance_provider.__wireup_registration__ = InjectableDeclaration(
        obj=_instance_provider,
        qualifier=qualifier,
        lifetime="singleton",
        as_type=as_type,
    )

    return _instance_provider
