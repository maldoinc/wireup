from __future__ import annotations

import importlib
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
"""Singleton DI container initialized for convenience"""


def wire(
    *,
    param: str | None = None,
    expr: str | None = None,
    qualifier: ContainerProxyQualifierValue = None,
) -> Callable[..., Any] | ParameterWrapper | ContainerProxy | Any:
    """Inject resources from the container to constructor or autowired method arguments.

    The arguments are exclusive and only one of them must be used at any time.

    :param param: Allows injecting a given parameter by name
    :param expr: Interpolate the templated string.
    Parameters inside ${} will be replaced with their corresponding value

    :param qualifier: Qualify which implementation to bind when there are multiple components
    implementing an interface that is registered in the container via @abstract.
    Can be used in conjunction with dep.
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
