from __future__ import annotations

from functools import singledispatch

from asgiref.sync import async_to_sync
from flask import Flask, g

from wireup._decorators import inject_from_container
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer, SyncContainer


def _inject_views(container: SyncContainer | AsyncContainer, app: Flask) -> None:
    inject_scoped = inject_from_container(container, get_request_container)

    app.view_functions = {name: inject_scoped(view) for name, view in app.view_functions.items()}


@singledispatch
def setup(container: SyncContainer | AsyncContainer, app: Flask) -> None:
    """Integrate Wireup with Flask.

    Setup performs the following:
    * Injects dependencies into Flask views.
    * Creates a new container scope for each request, with a scoped lifetime matching the request duration.
    """
    msg = "Unsupported type"
    raise NotImplementedError(msg)


@setup.register
def setup_sync(container: SyncContainer, app: Flask) -> None:
    def _before_request() -> None:
        ctx = container.enter_scope()
        g.wireup_container_ctx = ctx
        g.wireup_container = ctx.__enter__()

    def _teardown_request(exc: BaseException | None = None) -> None:
        if ctx := getattr(g, "wireup_container_ctx", None):
            ctx.__exit__(type(exc) if exc else None, exc, exc.__traceback__ if exc else None)

    app.before_request(_before_request)
    app.teardown_request(_teardown_request)

    _inject_views(container, app)
    app.wireup_container = container  # type: ignore[reportAttributeAccessIssue]


@setup.register
def setup_async(container: AsyncContainer, app: Flask) -> None:
    def _before_request() -> None:
        ctx = container.enter_scope()
        g.wireup_container_ctx = ctx
        g.wireup_container = async_to_sync(ctx.__aenter__)()

    def _teardown_request(exc: BaseException | None = None) -> None:
        if ctx := getattr(g, "wireup_container_ctx", None):
            async_to_sync(ctx.__aexit__)(type(exc) if exc else None, exc, exc.__traceback__ if exc else None)

    app.before_request(_before_request)
    app.teardown_request(_teardown_request)

    _inject_views(container, app)
    app.wireup_container = container


def get_app_container(app: Flask) -> SyncContainer | AsyncContainer:
    """Return the container associated with the given application."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]


def get_request_container() -> ScopedSyncContainer | ScopedAsyncContainer:
    """Return the container handling the current request."""
    return g.wireup_container
