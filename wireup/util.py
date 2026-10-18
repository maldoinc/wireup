from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wireup.ioc.types import AnyCallable, Qualifier


def stringify_type(target: type | AnyCallable) -> str:
    return repr(target)


def format_name(klass: type | AnyCallable, qualifier: Qualifier | None) -> str:
    qualifier_str = f" with qualifier '{qualifier}'" if qualifier else ""
    return f"{stringify_type(klass)}{qualifier_str}"


def qualified(klass: type[Any], qualifier: Qualifier) -> tuple[type[Any], Qualifier]:
    """Build a qualified dependency identifier."""
    return klass, qualifier
