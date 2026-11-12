from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from typing_extensions import TypeForm

if TYPE_CHECKING:
    from wireup.ioc.types import AnyCallable, Qualifier


def stringify_type(target: TypeForm[Any] | AnyCallable) -> str:
    return repr(target)


def format_name(klass: TypeForm[Any] | AnyCallable, qualifier: Qualifier | None) -> str:
    qualifier_str = f" with qualifier '{qualifier}'" if qualifier else ""
    return f"{stringify_type(klass)}{qualifier_str}"


T = TypeVar("T")


def qualified(klass: TypeForm[T], qualifier: Qualifier) -> tuple[TypeForm[T], Qualifier]:
    """Build a qualified dependency identifier."""
    return klass, qualifier
