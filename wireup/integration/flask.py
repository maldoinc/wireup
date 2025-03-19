from flask import Flask, Response, g

from wireup._decorators import inject_from_container
from wireup.integration.util import is_view_using_container
from wireup.ioc.container.sync_container import ScopedSyncContainer, SyncContainer


def _inject_views(container: SyncContainer, app: Flask) -> None:
    inject_scoped = inject_from_container(container, get_request_container)

    app.view_functions = {
        name: inject_scoped(view) if is_view_using_container(container, view) else view
        for name, view in app.view_functions.items()
    }


def setup(container: SyncContainer, app: Flask) -> None:
    """Integrate Wireup with Flask.

    This setup performs the following:
    * Injects dependencies into Flask views.
    * Creates a new container scope for each request, with a scoped lifetime matching the request duration.
    """

    def _before_request() -> None:
        ctx = container.enter_scope()
        g.wireup_container_ctx = ctx
        g.wireup_container = ctx.__enter__()

    def _after_request(response: Response) -> Response:
        g.wireup_container_ctx.__exit__(None, None, None)

        return response

    app.before_request(_before_request)
    app.after_request(_after_request)

    _inject_views(container, app)
    app.wireup_container = container  # type: ignore[reportAttributeAccessIssue]


def get_app_container(app: Flask) -> SyncContainer:
    """Return the container associated with the given application."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]


def get_request_container() -> ScopedSyncContainer:
    """Return the container handling the current request."""
    return g.wireup_container
