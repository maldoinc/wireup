from flask import Flask

from wireup import DependencyContainer
from wireup.integration.util import is_view_using_container


def _autowire_views(container: DependencyContainer, app: Flask) -> None:
    app.view_functions = {
        name: container.autowire(view) if is_view_using_container(container, view) else view
        for name, view in app.view_functions.items()
    }


def setup(container: DependencyContainer, app: Flask, *, import_flask_config: bool = False) -> None:
    """Integrate Wireup with Flask.

    This can import Flask config in the container and will automatically inject dependencies on
    Flask views.
    """
    if import_flask_config:
        container.params.update(dict(app.config.items()))  # type: ignore[reportArgumentType]

    _autowire_views(container, app)
    app.wireup_container = container  # type: ignore[reportAttributeAccessIssue]


def get_container(app: Flask) -> DependencyContainer:
    """Return the container associated with the given Flask application."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]
