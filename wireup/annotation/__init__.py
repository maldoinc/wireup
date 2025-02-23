from __future__ import annotations

import contextlib
import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, overload

from wireup.ioc.types import (
    EmptyContainerInjectionRequest,
    InjectableType,
    ParameterWrapper,
    Qualifier,
    ServiceLifetime,
    ServiceQualifier,
    TemplatedString,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def Inject(  # noqa: N802
    *,
    param: str | None = None,
    expr: str | None = None,
    qualifier: Qualifier | None = None,
) -> InjectableType | Callable[[], InjectableType]:
    """Let the container know this argument must be injected.

    This should be used where additional metadata is required for injection.

    :param param: Inject a given parameter by name.
    :param expr: Inject a string value using a templated string.
    Parameters inside `${}` will be replaced with their corresponding value.

    :param qualifier: Qualify which implementation to bind when there are multiple components
    implementing an interface that is registered in the container via `@abstract`.
    """
    res: InjectableType

    if param:
        res = ParameterWrapper(param)
    elif expr:
        res = ParameterWrapper(TemplatedString(expr))
    elif qualifier:
        res = ServiceQualifier(qualifier)
    else:
        res = EmptyContainerInjectionRequest()

    # Fastapi needs all dependencies to be wrapped with Depends.
    with contextlib.suppress(ModuleNotFoundError):

        def _inner() -> InjectableType:
            return res

        # This will act as a flag so that wireup knows this dependency belongs to it.
        _inner.__is_wireup_depends__ = True  # type: ignore[attr-defined]
        return importlib.import_module("fastapi").Depends(_inner)  # type: ignore[no-any-return]

    return res


T = TypeVar("T")


@dataclass
class ServiceDeclaration:
    """Object containing service declaration metadata."""

    obj: Any
    qualifier: Qualifier | None = None
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON


class AbstractDeclaration:
    """Used to denote a registration for a service that is abstract."""


@overload
def service(
    obj: None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> Callable[[T], T]:
    pass


@overload
def service(
    obj: T,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> T:
    pass


def service(
    obj: T | None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> T | Callable[[T], T]:
    """Mark the decorated class as a service.

    If used on a function it will register it as a factory for the class
    denoted by its return type.
    """
    # Allow this to be used as a decorator factory or as a decorator directly.
    if obj is None:

        def decorator(decorated_obj: T) -> T:
            decorated_obj.__wireup_registration__ = ServiceDeclaration(  # type: ignore[attr-defined]
                obj=decorated_obj, qualifier=qualifier, lifetime=lifetime
            )
            return decorated_obj

        return decorator

    obj.__wireup_registration__ = ServiceDeclaration(obj=obj)  # type: ignore[attr-defined]

    return obj


def abstract(cls: type[T]) -> type[T]:
    """Mark the decorated class as a service."""
    cls.__wireup_registration__ = AbstractDeclaration()  # type: ignore[attr-defined]

    return cls


__all__ = [
    "AbstractDeclaration",
    "Inject",
    "ServiceDeclaration",
    "abstract",
    "service",
]
