from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup import DependencyContainer, container, initialize_container
from wireup.integration import _BaseIntegration
from wireup.integration.util import is_view_using_container

if TYPE_CHECKING:
    from collections.abc import Hashable
    from types import ModuleType

    from flask import Flask


def _autowire_views(container: DependencyContainer, app: Flask) -> None:
    app.view_functions = {
        name: container.autowire(view) if is_view_using_container(container, view) else view
        for name, view in app.view_functions.items()
    }


def wireup_init_flask_integration(
    flask_app: Flask,
    service_modules: list[ModuleType],
    dependency_container: DependencyContainer = container,
    config_prefix: str | None = None,
) -> None:
    """Integrate wireup with a flask application.

    This must be called once all flask configuration and views have been registered.
     Updates the container with flask configuration and decorates all views where container objects
     are being used making the `@container.autowire` decorator no longer needed.

    :param flask_app: The flask application instance
    :param service_modules: A list of python modules where application services reside. These will be loaded to trigger
    container registrations.
    :param dependency_container: The instance of the dependency container.
    The default wireup singleton will be used when this is unset.
    This will be a noop and have no performance penalty for views which do not use the container.
    :param config_prefix: If set to a value all registered configuration will be prefixed with config and be accessible
    via "prefix.config_name". E.g: app.DEBUG.
    """
    config: dict[str, Any] = flask_app.config
    if config_prefix:
        config = {f"{config_prefix}.{name}": val for name, val in config.items()}

    dependency_container.params.update(config)
    initialize_container(dependency_container, service_modules=service_modules)
    _autowire_views(dependency_container, flask_app)


class FlaskIntegration(_BaseIntegration):
    def __init__(
        self,
        container: DependencyContainer,
        app: Flask,
        *,
        import_flask_config: bool,
    ) -> None:
        super().__init__(container)
        self.app = app
        self.import_flask_config = import_flask_config

    def get_key(self) -> Hashable:
        return self.app

    def setup(self) -> None:
        _autowire_views(self.container, self.app)

    def get_parameters(self) -> dict[str, Any]:
        return self.app.config if self.import_flask_config else {}
