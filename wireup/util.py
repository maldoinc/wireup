from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wireup.ioc.types import AnyCallable, Qualifier


def stringify_type(target: type | AnyCallable) -> str:
    if hasattr(target, "__name__") and hasattr(target, "__module__"):
        return f"{type(target).__name__.capitalize()} {target.__module__}.{target.__name__}"

    return str(target)


def format_name(klass: type | AnyCallable, qualifier: Qualifier | None) -> str:
    qualifier_str = f" with qualifier '{qualifier}'" if qualifier else ""
    return f"{stringify_type(klass)}{qualifier_str}"
