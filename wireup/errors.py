from __future__ import annotations

import json
import re
import sys
from collections.abc import Hashable
from collections.abc import Mapping as AbcMapping
from collections.abc import Sequence as AbcSequence
from typing import TYPE_CHECKING, Any, get_args, get_origin

from wireup.util import format_name, stringify_type

if TYPE_CHECKING:
    from wireup.ioc.types import AnyCallable, Qualifier


_INJECTABLES_DOC_URL = "https://maldoinc.github.io/wireup/latest/injectables/"


def _format_type_full_name(klass: Any) -> str:
    if isinstance(klass, type):
        return f"{klass.__module__}.{klass.__qualname__}"
    return repr(klass)


def _format_type_short_name(klass: Any) -> str:
    if isinstance(klass, type):
        return klass.__name__
    return getattr(klass, "__name__", repr(klass))


def _format_qualifier_code(qualifier: Qualifier) -> str:
    if isinstance(qualifier, str):
        return json.dumps(qualifier)
    return repr(qualifier)


def _format_qualifier_label(qualifier: Qualifier | None) -> str:
    if qualifier is None:
        return "(default)"
    return _format_qualifier_code(qualifier)


def _format_decorator(qualifier: Qualifier | None) -> str:
    if qualifier is None:
        return "@injectable"
    return f"@injectable(qualifier={_format_qualifier_code(qualifier)})"


def _to_factory_name(short_name: str) -> str:
    cleaned = short_name.lstrip("_")
    if not cleaned or not cleaned.isidentifier():
        return "create_instance"
    step1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", cleaned)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step1).lower()
    return f"create_{snake}"


def _format_provider(provider: AnyCallable) -> str:
    if isinstance(provider, type):
        return f"class {provider.__name__}"
    provider_name = getattr(provider, "__name__", repr(provider))
    return f"{provider_name}()"


def _format_unregistered_service_message(
    *,
    header: str,
    full_name: str,
    short_name: str,
    qualifier: Qualifier | None,
    is_async: bool,
) -> str:
    decorator = _format_decorator(qualifier)
    container_fn = "create_async_container" if is_async else "create_sync_container"
    direct_line = f"injectables=[{short_name}],"
    package_line = "injectables=[app.services],"
    pad_width = max(len(direct_line), len(package_line)) + 2

    return (
        f"{header}\n\n"
        f"Type '{full_name}' is not known to the container.\n\n"
        "How to fix:\n"
        "  Register it with the container using @injectable:\n\n"
        f"    {decorator}\n"
        f"    class {short_name}: ...\n\n"
        "  Then include it in your container:\n"
        f"    container = wireup.{container_fn}(\n"
        f"        {direct_line.ljust(pad_width)}# Direct registration\n"
        "        # or\n"
        f"        {package_line.ljust(pad_width)}# Package registration\n"
        "    )\n\n"
        f"Documentation: {_INJECTABLES_DOC_URL}"
    )


def _format_unknown_qualifier_message(
    *,
    header: str,
    full_name: str,
    short_name: str,
    qualifier: Qualifier | None,
    registrations: AbcSequence[tuple[Qualifier | None, AnyCallable]],
) -> str:
    ordered = sorted(registrations, key=lambda item: item[0] is not None)
    labeled = [
        (_format_qualifier_label(reg_qualifier), _format_provider(provider)) for reg_qualifier, provider in ordered
    ]
    max_label_len = max(len(label) for label, _ in labeled)
    available_lines = "\n".join(
        f"  {label.ljust(max_label_len)} -> registered via {provider}" for label, provider in labeled
    )

    decorator = _format_decorator(qualifier)
    has_class_registration = any(isinstance(provider, type) for _, provider in ordered)
    has_factory_registration = any(not isinstance(provider, type) for _, provider in ordered)

    examples: list[str] = []
    if has_class_registration:
        examples.append(f"    {decorator}\n    class {short_name}: ...")
    if has_factory_registration:
        factory_name = _to_factory_name(short_name)
        examples.append(f"    {decorator}\n    def {factory_name}() -> {short_name}: ...")
    examples_block = "\n\n".join(examples)

    if qualifier is not None:
        reason = f"Type '{full_name}' is registered, but not with the qualifier {qualifier!r}."
        option2_header = f"  Option 2: Register with the {qualifier!r} qualifier:"
    else:
        reason = f"Type '{full_name}' is registered, but not without a qualifier."
        option2_header = "  Option 2: Register without a qualifier:"

    return (
        f"{header}\n\n"
        f"{reason}\n\n"
        "Available qualifiers:\n"
        f"{available_lines}\n\n"
        "How to fix:\n"
        "  Option 1: Use an existing qualifier.\n\n"
        f"{option2_header}\n"
        f"{examples_block}\n\n"
        f"Documentation: {_INJECTABLES_DOC_URL}"
    )


def try_get_wireup_collection_replacement(type_hint: Any) -> Any | None:
    """Return the Wireup collection type for unsupported aliases."""
    return try_get_wireup_sequence_replacement(type_hint) or try_get_wireup_mapping_replacement(type_hint)


def try_get_wireup_sequence_replacement(type_hint: Any) -> Any | None:
    """Return collection type replacement for typing.Sequence[T] if applicable."""
    if getattr(type_hint, "__module__", None) != "typing":
        return None

    if get_origin(type_hint) is not AbcSequence:
        return None

    args = get_args(type_hint)
    return AbcSequence[args] if args else AbcSequence  # type:ignore[valid-type]


def try_get_wireup_mapping_replacement(type_hint: Any) -> Any | None:
    """Return collection type replacement for typing.Mapping[K, V] if applicable."""
    if getattr(type_hint, "__module__", None) != "typing":
        return None

    if get_origin(type_hint) is not AbcMapping:
        return None

    args = get_args(type_hint)
    if not args:
        return AbcMapping
    return AbcMapping[Hashable, args[1]]  # type:ignore[valid-type]


def get_unknown_collection_message(
    *,
    action: str,
    klass: Any,
    qualifier: Qualifier | None = None,
) -> str | None:
    if suggested_replacement_type := try_get_wireup_collection_replacement(klass):
        return (
            f"Cannot {action} unknown injectable {format_name(klass, qualifier)}. "
            f"Wireup collection injection uses {suggested_replacement_type!r}, not {klass!r}."
        )

    return None


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

    def __init__(
        self,
        klass: Any,
        qualifier: Qualifier | None = None,
        *,
        registrations: AbcSequence[tuple[Qualifier | None, AnyCallable]] | None = None,
        is_async: bool = False,
    ) -> None:
        self.klass = klass
        self.qualifier = qualifier

        if collection_message := get_unknown_collection_message(action="create", klass=klass, qualifier=qualifier):
            super().__init__(collection_message)
            return

        full_name = _format_type_full_name(klass)
        short_name = _format_type_short_name(klass)
        qualifier_suffix = f" with qualifier {qualifier!r}" if qualifier is not None else ""
        header = f"Cannot create '{full_name}'{qualifier_suffix}"

        if registrations:
            msg = _format_unknown_qualifier_message(
                header=header,
                full_name=full_name,
                short_name=short_name,
                qualifier=qualifier,
                registrations=registrations,
            )
        else:
            msg = _format_unregistered_service_message(
                header=header,
                full_name=full_name,
                short_name=short_name,
                qualifier=qualifier,
                is_async=is_async,
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
        if collection_message := get_unknown_collection_message(action="override", klass=klass, qualifier=qualifier):
            super().__init__(collection_message)
            return

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
