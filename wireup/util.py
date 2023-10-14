from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup import DependencyContainer, import_all_in_module

if TYPE_CHECKING:
    from types import ModuleType


def warmup_container(dependency_container: DependencyContainer[Any], service_modules: list[ModuleType]) -> None:
    """Import all modules provided in `service_modules` and initializes all registered singleton services.

    !!! note
        For long-lived processes this should be executed once at startup.
    """
    for module in service_modules:
        import_all_in_module(module)

    dependency_container.warmup()
