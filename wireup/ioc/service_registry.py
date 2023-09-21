from __future__ import annotations

import inspect
from collections import defaultdict
from inspect import Parameter
from typing import Any, Callable, TypeVar

from wireup.ioc.container_util import (
    ContainerProxyQualifierValue,
    _ContainerClassMetadata,
    _ContainerTargetMeta,
)

__T = TypeVar("__T")


class _ServiceRegistry:
    def __init__(self) -> None:
        self.known_interfaces: dict[type[__T], dict[str, type[__T]]] = {}
        self.known_impls: dict[type[__T], set[str]] = defaultdict(set)
        self.factory_functions: dict[type[__T], Callable[..., __T]] = {}

        self.class_meta: dict[__T, _ContainerClassMetadata] = {}
        self.targets_meta: dict[__T, _ContainerTargetMeta] = {}

    def register_service(
        self,
        klass: type[__T],
        qualifier: ContainerProxyQualifierValue,
        *,
        singleton: bool,
    ) -> None:
        if self.is_type_with_qualifier_known(klass, qualifier):
            msg = f"Cannot register type {klass} with qualifier '{qualifier}' as it already exists."
            raise ValueError(msg)

        if self.is_interface_known(klass.__base__):
            if qualifier in self.known_interfaces[klass.__base__]:
                msg = (
                    f"Cannot register implementation class {klass} for {klass.__base__} "
                    f"with qualifier '{qualifier}' as it already exists"
                )
                raise ValueError(msg)

            self.known_interfaces[klass.__base__][qualifier] = klass

        self.known_impls[klass].add(qualifier)
        self.__register_impl_meta(klass, singleton=singleton)

    def register_abstract(self, klass: type[__T]) -> None:
        self.known_interfaces[klass] = defaultdict()

    def register_factory(self, fn: Callable[[], __T], *, singleton: bool) -> None:
        return_type = inspect.signature(fn).return_annotation

        if return_type is Parameter.empty:
            msg = "Factory functions must specify a return type denoting the type of dependency it can create."
            raise ValueError(msg)

        if self.is_impl_known_from_factory(return_type):
            msg = f"A function is already registered as a factory for dependency type {return_type}."
            raise ValueError(msg)

        if self.is_impl_known(return_type):
            msg = f"Cannot register factory function as type {return_type} is already known by the container."
            raise ValueError(msg)

        self.__register_impl_meta(return_type, singleton=singleton)
        self.register_targets_meta(fn)
        self.factory_functions[return_type] = fn

    def register_targets_meta(self, fn: Callable[..., Any]) -> None:
        if fn not in self.targets_meta:
            self.targets_meta[fn] = _ContainerTargetMeta(signature=inspect.signature(fn))

    def __register_impl_meta(self, klass: __T, *, singleton: bool) -> None:
        self.class_meta[klass] = _ContainerClassMetadata(singleton=singleton, signature=inspect.signature(klass))

    def is_impl_known(self, klass: type[__T]) -> bool:
        return klass in self.known_impls

    def is_impl_with_qualifier_known(self, klass: type[__T], qualifier_value: ContainerProxyQualifierValue) -> bool:
        return klass in self.known_impls and qualifier_value in self.known_impls[klass]

    def is_type_with_qualifier_known(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> bool:
        is_known_impl = self.is_impl_with_qualifier_known(klass, qualifier)
        is_known_intf = self.__is_interface_with_qualifier_known(klass, qualifier)
        is_known_from_factory = self.is_impl_known_from_factory(klass)

        return is_known_impl or is_known_intf or is_known_from_factory

    def __is_interface_with_qualifier_known(
        self,
        klass: type[__T],
        qualifier: ContainerProxyQualifierValue,
    ) -> bool:
        return klass in self.known_interfaces and qualifier in self.known_interfaces[klass]

    def is_impl_known_from_factory(self, klass: type[__T]) -> bool:
        return klass in self.factory_functions

    def is_impl_singleton(self, klass: __T) -> bool:
        meta = self.class_meta.get(klass)

        return meta and meta.singleton

    def is_interface_known(self, klass: type[__T]) -> bool:
        return klass in self.known_interfaces
