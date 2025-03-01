from flask import Flask, Response, g

from wireup.decorators import make_inject_decorator
from wireup.integration.util import is_view_using_container
from wireup.ioc.container.sync_container import SyncContainer


def _inject_views(container: SyncContainer, app: Flask) -> None:
    inject_scoped = make_inject_decorator(container, lambda: g.wireup_container)

    app.view_functions = {
        name: inject_scoped(view) if is_view_using_container(container, view) else view
        for name, view in app.view_functions.items()
    }


def setup(container: SyncContainer, app: Flask) -> None:
    """Integrate Wireup with Flask.

    This can import Flask config in the container and will automatically inject dependencies in views.
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


def get_container(app: Flask) -> SyncContainer:
    """Return the container associated with the given application."""
    try:
        return g.wireup_container
    except RuntimeError:
        return app.wireup_container  # type: ignore[reportAttributeAccessIssue]
