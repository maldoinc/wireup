from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Union


@dataclass(frozen=True)
class TemplatedString:
    value: str


ParameterReference = Union[str, TemplatedString]


@dataclass(frozen=True)
class ParameterWrapper:
    param: ParameterReference


@dataclass(frozen=True)
class ContainerProxyQualifier:
    qualifier: str


ContainerParameterInitializationType = Union[ContainerProxyQualifier, ParameterWrapper]


class DependencyInitializationContext:
    context: dict[type, dict[str, ParameterWrapper]] = defaultdict(dict)

    def add_param(self, klass: type, argument_name, parameter_ref: ParameterReference):
        self.context[klass][argument_name] = ParameterWrapper(parameter_ref)

    def update(self, klass: type, params: dict[str, ParameterReference]):
        self.context[klass].update({k: ParameterWrapper(v) for k, v in params.items()})


class ContainerProxy:
    def __init__(self, instance_supplier: Callable) -> None:
        self.__supplier = instance_supplier
        self.__proxy_object = None

    def __getattr__(self, name: Any) -> Any:
        if not self.__proxy_object:
            self.__proxy_object = self.__supplier()

        return getattr(self.__proxy_object, name)


@dataclass(frozen=True, eq=True)
class _InitializedObjectIdentifier:
    """Identifies a dependency instance.

    Used to store and retrieve instances from the in-memory cache.
    """

    class_type: type
    qualifier: str | None
