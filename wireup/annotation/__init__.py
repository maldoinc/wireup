from __future__ import annotations

import contextlib
import importlib
import warnings
from enum import Enum
from typing import TYPE_CHECKING

from wireup.ioc.types import (
    ContainerProxyQualifier,
    EmptyContainerInjectionRequest,
    InjectableType,
    ParameterWrapper,
    Qualifier,
    TemplatedString,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def wire(
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


class ParameterEnum(Enum):
    """Enum with a `.wire` method allowing easy injection of members.

    Allows you to add application parameters as enum members and their names as values.
    When you need to inject a parameter instead of referencing it by name you can
    annotate the parameter with the wire function call or set that as the default value.

    This will inject a parameter by name and won't work with expressions.
    """

    def wire(self) -> InjectableType | Callable[[], InjectableType]:
        """Inject the parameter this enumeration member represents.

        Equivalent of `wire(param=EnumParam.enum_member.value)`
        """
        warnings.warn(
            "ParameterEnum is deprecated. Please use type aliases instead. "
            "E.g.: SomeParam = Annotated[str, Wire(..)]",
            stacklevel=2,
        )

        return wire(param=self.value)


Wire = wire
"""Alias of `wire`. Meant to be used with `Annotated`."""

__all__ = ["ParameterEnum", "Wire", "wire"]
