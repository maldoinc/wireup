from __future__ import annotations

import contextlib
import importlib
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, overload

from typing_extensions import Annotated

from wireup.ioc.types import (
    ConfigInjectionRequest,
    EmptyContainerInjectionRequest,
    InjectableType,
    Qualifier,
    ServiceLifetime,
    ServiceQualifier,
    TemplatedString,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def Inject(  # noqa: N802
    *,
    config: str | None = None,
    param: str | None = None,
    expr: str | None = None,
    qualifier: Qualifier | None = None,
) -> InjectableType:
    """Let the Wireup container know it must inject this parameter.

    When used without parameters as `Annotated[T, Inject()]`,
    you can also use the alias `Injected[T]`.

    :param config: Inject a specific config by name.
    :param param: Deprecated. Use `Inject(config="")` instead.
    :param expr: Inject a string value using a templated string.
    Parameters within `${}` will be replaced with their corresponding values.

    :param qualifier: Specify which implementation to bind when multiple components
    implement an interface registered in the container via `@abstract`.
    """
    res: InjectableType
    if config:
        res = ConfigInjectionRequest(config)
    elif param:
        msg = f'Parameters have been renamed to Config. Use `Inject(config="{param}")` instead.'
        warnings.warn(msg, FutureWarning, stacklevel=2)
        res = ConfigInjectionRequest(param)
    elif expr:
        res = ConfigInjectionRequest(TemplatedString(expr))
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

Injected = Annotated[T, Inject()]
"""Let the Wireup container know it must inject this parameter.

Alias of `Annotated[T, Inject()]`.
"""


@dataclass
class ServiceDeclaration:
    """Object containing service declaration metadata."""

    obj: Any
    qualifier: Qualifier | None = None
    lifetime: ServiceLifetime = "singleton"


@dataclass
class AbstractDeclaration:
    """Used to denote a registration for a service that is abstract."""

    obj: Any


@overload
def injectable(
    obj: None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = "singleton",
) -> Callable[[T], T]:
    pass


@overload
def injectable(
    obj: T,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = "singleton",
) -> T:
    pass


def injectable(
    obj: T | None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = "singleton",
) -> T | Callable[[T], T]:
    """Mark the decorated class or function as a Wireup service."""

    # Allow this to be used as a decorator factory or as a decorator directly.
    def _service_decorator(decorated_obj: T) -> T:
        decorated_obj.__wireup_registration__ = ServiceDeclaration(  # type: ignore[attr-defined]
            obj=decorated_obj, qualifier=qualifier, lifetime=lifetime
        )
        return decorated_obj

    return _service_decorator if obj is None else _service_decorator(obj)


@overload
def service(
    obj: None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = "singleton",
) -> Callable[[T], T]:
    pass


@overload
def service(
    obj: T,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = "singleton",
) -> T:
    pass


def service(
    obj: T | None = None,
    *,
    qualifier: Qualifier | None = None,
    lifetime: ServiceLifetime = "singleton",
) -> T | Callable[[T], T]:
    """Mark the decorated class or function as a Wireup service.

    DEPRECATED: Use @injectable instead.
    """
    warnings.warn(
        "The @service decorator is deprecated and will be removed in a future version. Use @injectable instead.",
        FutureWarning,
        stacklevel=2,
    )
    return injectable(obj, qualifier=qualifier, lifetime=lifetime)


def abstract(cls: type[T]) -> type[T]:
    """Mark the decorated class as an abstract service."""
    cls.__wireup_registration__ = AbstractDeclaration(cls)  # type: ignore[attr-defined]

    return cls
