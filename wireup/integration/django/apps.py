from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from django.apps import AppConfig
from django.conf import settings

from wireup import container, initialize_container

if TYPE_CHECKING:
    from wireup.integration.django import WireupSettings


class WireupConfig(AppConfig):
    """Integrate wireup with Django."""

    name = "wireup.integration.django"

    def ready(self) -> None:
        integration_settings: WireupSettings = settings.WIREUP

        initialize_container(
            container,
            parameters={
                entry: getattr(settings, entry)
                for entry in dir(settings)
                if not entry.startswith("__") and hasattr(settings, entry)
            },
            service_modules=[
                importlib.import_module(m) if isinstance(m, str) else m for m in integration_settings.service_modules
            ],
        )
