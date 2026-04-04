from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask, Response, g

from wireup._decorators import inject_from_container
from wireup.renderer._consumers import ConsumerMetadata
from wireup.renderer.full_page import GraphEndpointOptions, render_graph_page

if TYPE_CHECKING:
    from wireup.ioc.container.sync_container import ScopedSyncContainer, SyncContainer

__all__ = [
    "GraphEndpointOptions",
    "get_app_container",
    "get_request_container",
    "setup",
]


def _inject_views(container: SyncContainer, app: Flask) -> None:
    app.view_functions = {
        endpoint: inject_from_container(
            container,
            get_request_container,
            consumer_metadata=_flask_consumer_metadata(app, endpoint, view),
        )(view)
        for endpoint, view in app.view_functions.items()
    }


def _flask_consumer_metadata(app: Flask, endpoint: str, view: object) -> ConsumerMetadata:
    rules = sorted((rule for rule in app.url_map.iter_rules() if rule.endpoint == endpoint), key=lambda item: item.rule)
    paths = tuple(rule.rule for rule in rules)
    methods = tuple(dict.fromkeys(method for rule in rules for method in sorted(rule.methods - {"HEAD", "OPTIONS"})))
    method_label = "|".join(methods) if methods else "ROUTE"
    path_label = ", ".join(paths) if paths else endpoint
    consumer_id = f"{method_label} {path_label}"

    return ConsumerMetadata(
        consumer_id=consumer_id,
        kind="flask_route",
        label=f"🌐 {consumer_id}",
        group="Flask",
        module=getattr(view, "__module__", "unknown"),
    )


def _setup_graph_route(app: Flask, *, options: GraphEndpointOptions) -> None:
    @app.get("/_wireup")
    def _wireup_graph_page() -> Response:
        return Response(
            render_graph_page(
                get_app_container(app),
                title=f"{app.name} - Wireup Graph",
                options=options,
            ),
            mimetype="text/html",
        )


def setup(
    container: SyncContainer,
    app: Flask,
    *,
    add_graph_endpoint: bool = False,
    graph_endpoint_options: GraphEndpointOptions | None = None,
) -> None:
    """Integrate Wireup with Flask.

    Setup performs the following:
    * Injects dependencies into Flask views.
    * Creates a new container scope for each request, with a scoped lifetime matching the request duration.
    """

    def _before_request() -> None:
        ctx = container.enter_scope()
        g.wireup_container_ctx = ctx
        g.wireup_container = ctx.__enter__()

    def _teardown_request(exc: BaseException | None = None) -> None:
        if ctx := getattr(g, "wireup_container_ctx", None):
            ctx.__exit__(type(exc) if exc else None, exc, exc.__traceback__ if exc else None)

    app.before_request(_before_request)
    app.teardown_request(_teardown_request)

    if add_graph_endpoint:
        _setup_graph_route(app, options=graph_endpoint_options or GraphEndpointOptions())
    _inject_views(container, app)
    app.wireup_container = container  # type: ignore[reportAttributeAccessIssue]


def get_app_container(app: Flask) -> SyncContainer:
    """Return the container associated with the given application."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]


def get_request_container() -> ScopedSyncContainer:
    """Return the container handling the current request."""
    return g.wireup_container
