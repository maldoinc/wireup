from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


@dataclass(frozen=True)
class WireupSettings:
    """Class containing Wireup settings specific to Django."""

    service_modules: list[str | ModuleType]
    """List of modules containing wireup service registrations."""

    perform_warmup: bool = True
    """Setting this to true will cause the container to create
    instances of services at application startup.
    When set to false, services are created on first use.
    """
