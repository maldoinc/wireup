from __future__ import annotations

import importlib

from django.apps import AppConfig
from django.conf import settings

from wireup import container, warmup_container


class WireupConfig(AppConfig):
    """Integrate wireup with Django."""

    name = "wireup.integration.django"

    def ready(self) -> None:  # noqa: D102
        service_modules = settings.WIREUP.get("SERVICE_MODULES", [])

        for entry in dir(settings):
            if not entry.startswith("__") and hasattr(settings, entry):
                container.params.put(entry, getattr(settings, entry))

        warmup_container(container, [importlib.import_module(m) if isinstance(m, str) else m for m in service_modules])
