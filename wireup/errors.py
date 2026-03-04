from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from wireup.util import format_name, stringify_type

if TYPE_CHECKING:
    from wireup.ioc.types import AnyCallable, Qualifier


class WireupError(Exception):
    """Base type for all exceptions raised by wireup."""


class DuplicateServiceRegistrationError(WireupError):
    """Raised when attempting to register a injectable with the same qualifier twice."""

    def __init__(self, klass: type[Any], qualifier: Qualifier | None) -> None:
        self.klass = klass
        self.qualifier = qualifier

        super().__init__(f"Cannot register type {format_name(klass, qualifier)} as it already exists.")


class DuplicateQualifierForInterfaceError(WireupError):
    """Raised when registering an impl for an interface using a qualifier that is already known."""

    def __init__(self, klass: type[Any], qualifier: Qualifier | None) -> None:
        super().__init__(
            f"Cannot register implementation class {format_name(klass, qualifier)} for {klass.__base__} "
            "as it already exists",
        )


class UnknownParameterError(WireupError):
    """Raised when requesting a config by name which does not exist."""

    def __init__(self, parameter_name: str, parent_path: str | None = None) -> None:
        self.parameter_name = parameter_name

        if parent_path:
            message = (
                f"Unknown config key requested: '{parent_path}.{parameter_name}'."
                f" '{parameter_name}' not found in '{parent_path}'"
            )
        else:
            message = f"Unknown config key requested: '{parameter_name}'"

        super().__init__(message)


class FactoryReturnTypeIsEmptyError(WireupError):
    """Raised when a factory function has no return type defined."""

    def __init__(self, fn: AnyCallable) -> None:
        super().__init__(
            "Factories must specify a return type denoting the type of dependency it can create. "
            f"Please add a return type to {fn}"
        )


class UnknownQualifiedServiceRequestedError(WireupError):
    """Raised when requesting a type which exists but using an unknown qualifier."""

    def __init__(
        self,
        klass: type[Any],
        qualifier: Qualifier | None,
        available_qualifiers: set[Qualifier | None],
    ) -> None:
        self.klass = klass
        self.qualifier = qualifier
        qualifiers_str = ", ".join(sorted(f"'{q}'" for q in available_qualifiers))

        super().__init__(
            f"Cannot create {klass} as qualifier '{qualifier}' is unknown. Available qualifiers: [{qualifiers_str}].",
        )


class UnknownServiceRequestedError(WireupError):
    """Raised when requesting an unknown type."""

    def __init__(self, klass: Any, qualifier: Qualifier | None = None) -> None:
        msg = (
            f"Cannot create unknown injectable {format_name(klass, qualifier)}. "
            "Make sure it is registered with the container."
        )
        super().__init__(msg)


class InvalidRegistrationTypeError(WireupError):
    """Raised when attempting to register an invalid object type as a injectable."""

    def __init__(self, attempted: Any) -> None:
        super().__init__(f"Cannot register {attempted} with the container. Allowed types are callables and types.")


class AsTypeMismatchError(WireupError):
    """Raised when as_type registration does not match the implementation type."""

    def __init__(self, *, implementation: type[Any], as_type: type[Any]) -> None:
        super().__init__(
            f"Cannot register implementation {stringify_type(implementation)} as {stringify_type(as_type)}. "
            f"{stringify_type(implementation)} is not a subclass of {stringify_type(as_type)}."
        )


class InvalidAsTypeError(WireupError):
    """Raised when as_type is not a valid registration key."""

    def __init__(self, as_type: Any) -> None:
        super().__init__(
            f"Invalid as_type value {as_type!r}. as_type must be a runtime type usable as a registration key."
        )


class UnknownOverrideRequestedError(WireupError):
    """Raised when attempting to override a injectable which does not exist."""

    def __init__(self, klass: type, qualifier: Qualifier | None) -> None:
        super().__init__(f"Cannot override unknown {format_name(klass, qualifier)}.")


class PositionalOnlyParameterError(WireupError):
    """Raised when Wireup encounters a positional-only parameter that it must inject."""

    def __init__(self, name: str, target: Any) -> None:
        msg = (
            f"Cannot inject parameter '{name}' of '{stringify_type(target)}' because it is positional-only. "
            "Injection is performed by keyword arguments. Remove the '/' separator or move this parameter after it."
        )
        super().__init__(msg)


if sys.version_info >= (3, 11):

    class ContainerCloseError(ExceptionGroup, WireupError):  # noqa: F821
        """Contains a list of exceptions raised while closing the container."""

        def __init__(self, message: str, errors: list[Exception]) -> None:
            self.errors = errors
            super().__init__(message, errors)

else:

    class ContainerCloseError(WireupError):
        """Contains a list of exceptions raised while closing the container."""

        def __init__(self, message: str, errors: list[Exception]) -> None:
            self.errors = errors
            super().__init__(f"{message}: {errors}")
