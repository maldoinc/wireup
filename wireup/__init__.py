from __future__ import annotations

import importlib
from enum import Enum
from typing import Any, Callable

from wireup.ioc.container_util import (
    ContainerProxy,
    ContainerProxyQualifier,
    ContainerProxyQualifierValue,
    ParameterWrapper,
    TemplatedString,
)
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag

container = DependencyContainer(ParameterBag())
"""Singleton DI container instance.

Use when your application only needs one container.
"""


def wire(
    *,
    param: str | None = None,
    expr: str | None = None,
    qualifier: ContainerProxyQualifierValue = None,
) -> Callable[..., Any] | ParameterWrapper | ContainerProxy | Any:
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
    if param:
        return ParameterWrapper(param)

    if expr:
        return ParameterWrapper(TemplatedString(expr))

    if qualifier:
        return ContainerProxyQualifier(qualifier)

    try:
        # Allow fastapi users to do .get() without any params
        # It is meant to be used as a default value in where Depends() is expected
        return importlib.import_module("fastapi").Depends(lambda: None)
    except ModuleNotFoundError as e:
        msg = "One of param, expr or qualifier must be set"
        raise ValueError(msg) from e


class ParameterEnum(Enum):
    """Enum with a `.wire` method allowing easy injection of members.

    Allows you to add application parameters as enum members and their names as values.
    When you need to inject a parameter instead of referencing it by name you can
    simply set the enum as the default value.

    This will inject a parameter by name and won't work with expressions.
    """

    def wire(self) -> Any:
        """Inject the parameter this enumeration member represents.

        Equivalent of `wire(param=EnumParam.enum_member.value)`
        """
        return wire(param=self.value)
