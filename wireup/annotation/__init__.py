from __future__ import annotations

import contextlib
import importlib
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar, overload

from wireup.ioc.types import (
    ContainerProxyQualifier,
    EmptyContainerInjectionRequest,
    InjectableType,
    ParameterWrapper,
    Qualifier,
    ServiceLifetime,
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
    """Inject resources from the container to autowired method arguments.

    Arguments are exclusive and only one of them must be used at any time.
    !!! note
        Methods MUST be still decorated with autowire for this to work.

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
        res = ContainerProxyQualifier(qualifier)
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


def wire(
    *,
    param: str | None = None,
    expr: str | None = None,
    qualifier: Qualifier | None = None,
) -> InjectableType | Callable[[], InjectableType]:
    """Inject resources from the container to autowired method arguments."""
    warnings.warn(
        "Using Wire/wire aliases is deprecated. Prefer using Inject instead",
        stacklevel=2,
    )
    return Inject(param=param, expr=expr, qualifier=qualifier)


Wire = wire


class ParameterEnum(Enum):
    """Enum with a `.wire` method allowing easy injection of members.

    Allows you to add application parameters as enum members and their names as values.
    When you need to inject a parameter instead of referencing it by name you can
    annotate the parameter with the wire function call or set that as the default value.

    This will inject a parameter by name and won't work with expressions.
    """

    def wire(self) -> InjectableType | Callable[[], InjectableType]:
        """Inject the parameter this enumeration member represents.

        Equivalent of `Inject(param=EnumParam.enum_member.value)`
        """
        warnings.warn(
            "ParameterEnum is deprecated. Please use type aliases instead. "
            "E.g.: SomeParam = Annotated[str, Inject(..)]",
            stacklevel=2,
        )

        return Inject(param=self.value)


__T = TypeVar("__T")


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
) -> Callable[[__T], __T]:
    pass


@overload
def service(
    obj: __T,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> __T:
    pass


def service(
    obj: __T | None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> __T | Callable[[__T], __T]:
    """Mark the decorated class as a service.

    If used on a function it will register it as a factory for the class
    denoted by its return type.
    """
    # Allow this to be used as a decorator factory or as a decorator directly.
    if obj is None:

        def decorator(decorated_obj: __T) -> __T:
            decorated_obj.__wireup_registration__ = ServiceDeclaration(  # type: ignore[attr-defined]
                obj=decorated_obj, qualifier=qualifier, lifetime=lifetime
            )
            return decorated_obj

        return decorator

    obj.__wireup_registration__ = ServiceDeclaration(obj=obj)  # type: ignore[attr-defined]

    return obj


def abstract(cls: type[__T]) -> type[__T]:
    """Mark the decorated class as a service."""
    cls.__wireup_registration__ = AbstractDeclaration()  # type: ignore[attr-defined]

    return cls


__all__ = [
    "ParameterEnum",
    "AbstractDeclaration",
    "ServiceDeclaration",
    "abstract",
    "service",
    "wire",
    "Wire",
    "Inject",
]
