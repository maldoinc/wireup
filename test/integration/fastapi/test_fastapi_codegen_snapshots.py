from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from typing import Any

import pytest
import wireup
import wireup.integration.fastapi
from fastapi import FastAPI, Request, WebSocket
from fastapi.routing import APIRoute, APIWebSocketRoute
from wireup._annotations import Injected, injectable


@injectable
@dataclass
class _SnapshotSingletonService:
    pass


@injectable(lifetime="scoped")
@dataclass
class _SnapshotScopedService:
    pass


def _normalize_generated_code(code: str) -> str:
    # Generated context variable names contain UUID suffixes; normalize for stable snapshot assertions.
    return re.sub(r"_context_(type|value)_[0-9a-f]{32}", r"_context_\1_ID", code.strip())


def _get_generated_code(target: Any) -> str:
    if not hasattr(target, "__wireup_generated_code__"):
        pytest.fail("Target has no generated code.")

    return _normalize_generated_code(target.__wireup_generated_code__)


def _get_route(app: FastAPI, path: str, route_type: type[APIRoute | APIWebSocketRoute]) -> APIRoute | APIWebSocketRoute:
    for route in app.routes:
        if isinstance(route, route_type) and route.path == path:
            return route

    pytest.fail(f"No {route_type.__name__} found for {path}")


def test_codegen_http_without_request_param_skips_connection_context_when_scope_not_required() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotSingletonService])

    @app.get("/snap/http")
    async def endpoint(s: Injected[_SnapshotSingletonService]) -> None:
        _ = s

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    route = _get_route(app, "/snap/http", APIRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[_wireup_obj_s_obj_id].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code == expected


def test_codegen_http_with_request_param_skips_connection_context_when_scope_not_required() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotSingletonService])

    @app.get("/snap/http-request")
    async def endpoint(request: Request, s: Injected[_SnapshotSingletonService]) -> None:
        _ = request, s

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    route = _get_route(app, "/snap/http-request", APIRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[_wireup_obj_s_obj_id].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code == expected


def test_codegen_http_scoped_dependency_enters_scope_with_context() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotScopedService])

    @app.get("/snap/http-scoped")
    async def endpoint(sc: Injected[_SnapshotScopedService]) -> None:
        _ = sc

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    route = _get_route(app, "/snap/http-scoped", APIRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            async with _wireup_container.enter_scope({_context_type_ID: kwargs.pop('_fastapi_http_connection')}) as scope:
                kwargs['sc'] = _wireup_scoped_factories[_wireup_obj_sc_obj_id].factory(scope)
                return await _wireup_target(*args, **kwargs)
    """).strip()  # noqa: E501

    assert code == expected


def test_codegen_http_middleware_mode_uses_scoped_supplier() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotSingletonService, wireup.integration.fastapi])

    @app.get("/snap/http-middleware")
    async def endpoint(s: Injected[_SnapshotSingletonService]) -> None:
        _ = s

    wireup.integration.fastapi.setup(container, app, middleware_mode=True)
    route = _get_route(app, "/snap/http-middleware", APIRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = _wireup_singleton_factories[_wireup_obj_s_obj_id].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code == expected


def test_codegen_websocket_without_param_skips_connection_context_when_scope_not_required() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotSingletonService])

    @app.websocket("/snap/ws")
    async def endpoint(s: Injected[_SnapshotSingletonService]) -> None:
        _ = s

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    route = _get_route(app, "/snap/ws", APIWebSocketRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[_wireup_obj_s_obj_id].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code == expected


def test_codegen_websocket_middleware_mode_skips_connection_context_when_scope_not_required() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotSingletonService, wireup.integration.fastapi])

    @app.websocket("/snap/ws-middleware")
    async def endpoint(s: Injected[_SnapshotSingletonService]) -> None:
        _ = s

    wireup.integration.fastapi.setup(container, app, middleware_mode=True)
    route = _get_route(app, "/snap/ws-middleware", APIWebSocketRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[_wireup_obj_s_obj_id].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code == expected


def test_codegen_websocket_scoped_dependency_enters_scope_with_context() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotScopedService])

    @app.websocket("/snap/ws-scoped")
    async def endpoint(sc: Injected[_SnapshotScopedService]) -> None:
        _ = sc

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    route = _get_route(app, "/snap/ws-scoped", APIWebSocketRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            async with _wireup_container.enter_scope({_context_type_ID: kwargs.pop('_fastapi_http_connection')}) as scope:
                kwargs['sc'] = _wireup_scoped_factories[_wireup_obj_sc_obj_id].factory(scope)
                return await _wireup_target(*args, **kwargs)
    """).strip()  # noqa: E501

    assert code == expected


def test_codegen_websocket_scoped_dependency_in_middleware_mode_enters_scope_with_context() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotScopedService, wireup.integration.fastapi])

    @app.websocket("/snap/ws-scoped-middleware")
    async def endpoint(sc: Injected[_SnapshotScopedService]) -> None:
        _ = sc

    wireup.integration.fastapi.setup(container, app, middleware_mode=True)
    route = _get_route(app, "/snap/ws-scoped-middleware", APIWebSocketRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            async with _wireup_container.enter_scope({_context_type_ID: kwargs.pop('_fastapi_http_connection')}) as scope:
                kwargs['sc'] = _wireup_scoped_factories[_wireup_obj_sc_obj_id].factory(scope)
                return await _wireup_target(*args, **kwargs)
    """).strip()  # noqa: E501

    assert code == expected


def test_codegen_websocket_with_explicit_param_and_scoped_dependency_uses_synthetic_connection_param() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[_SnapshotScopedService])

    @app.websocket("/snap/ws-scoped-explicit")
    async def endpoint(websocket: WebSocket, sc: Injected[_SnapshotScopedService]) -> None:
        _ = websocket, sc

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    route = _get_route(app, "/snap/ws-scoped-explicit", APIWebSocketRoute)
    code = _get_generated_code(route.dependant.call)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            async with _wireup_container.enter_scope({_context_type_ID: kwargs.pop('_fastapi_http_connection')}) as scope:
                kwargs['sc'] = _wireup_scoped_factories[_wireup_obj_sc_obj_id].factory(scope)
                return await _wireup_target(*args, **kwargs)
    """).strip()  # noqa: E501

    assert code == expected
