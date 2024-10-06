from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from fastapi import FastAPI

from wireup import DependencyContainer, container, initialize_container
from wireup.integration.fastapi import _autowire_views

if TYPE_CHECKING:
    from types import ModuleType

    from fastapi import FastAPI

    from wireup.ioc.dependency_container import DependencyContainer


def wireup_init_fastapi_integration(
    app: FastAPI,
    service_modules: list[ModuleType],
    dependency_container: DependencyContainer = container,
) -> None:
    """Integrate wireup with a fastapi application.

    This must be called once all views have been registered.
     Decorates all views where container objects are being used making
     the `@container.autowire` decorator no longer needed.

    :param app: The application instance
    :param service_modules: A list of python modules where application services reside. These will be loaded to trigger
    container registrations.
    :param dependency_container: The instance of the dependency container.
    The default wireup singleton will be used when this is unset.
    This will be a noop and have no performance penalty for views which do not use the container.
    """
    warnings.warn(
        "Using wireup_init_fastapi_integration is deprecated. "
        "Use wireup.create_container in conjunction with wireup.integration.fastapi.setup. "
        "See: https://maldoinc.github.io/wireup/latest/integrations/fastapi/",
        DeprecationWarning,
        stacklevel=2,
    )
    initialize_container(dependency_container, service_modules=service_modules)
    _autowire_views(dependency_container, app)
