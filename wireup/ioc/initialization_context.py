from __future__ import annotations

from typing import TYPE_CHECKING, Union

from wireup.ioc.types import AnyCallable

if TYPE_CHECKING:
    from wireup.ioc.types import AnnotatedParameter, ServiceLifetime

InjectionTarget = Union[AnyCallable, type]
"""Represents valid dependency injection targets: Functions and Classes."""


class InitializationContext:
    __slots__ = ("dependencies", "lifetime")

    def __init__(self) -> None:
        self.dependencies: dict[InjectionTarget, dict[str, AnnotatedParameter]] = {}
        self.lifetime: dict[InjectionTarget, ServiceLifetime] = {}

    def init_target(self, target: InjectionTarget, lifetime: ServiceLifetime | None = None) -> bool:
        if target in self.dependencies:
            return False

        self.dependencies[target] = {}

        if lifetime is not None:
            self.lifetime[target] = lifetime

        return True

    def add_dependency(self, target: InjectionTarget, parameter_name: str, value: AnnotatedParameter) -> None:
        self.dependencies[target][parameter_name] = value

    def remove_dependencies(self, target: InjectionTarget, names_to_remove: set[str]) -> None:
        self.dependencies[target] = {k: v for k, v in self.dependencies[target].items() if k not in names_to_remove}

    def remove_dependency_type(self, target: InjectionTarget, type_to_remove: type) -> None:
        self.dependencies[target] = {k: v for k, v in self.dependencies[target].items() if v.klass != type_to_remove}
