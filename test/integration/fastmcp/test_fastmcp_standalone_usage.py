import asyncio

import httpx
import wireup
import wireup.integration.fastapi
import wireup.integration.fastmcp
import wireup.integration.starlette
from fastapi import FastAPI
from fastmcp import Client, FastMCP
from fastmcp.client.transports.http import StreamableHttpTransport
from starlette.applications import Starlette
from starlette.routing import Mount
from wireup import Injected
from wireup.integration.fastapi import inject as inject_fastapi
from wireup.integration.starlette import inject as inject_starlette

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


def _make_transport(app: object, path: str = "/mcp") -> StreamableHttpTransport:
    def httpx_client_factory(**kwargs: object) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),  # type: ignore[arg-type]
            base_url="http://test",
            headers=kwargs.get("headers"),
            auth=kwargs.get("auth"),
            follow_redirects=bool(kwargs.get("follow_redirects", True)),
            timeout=kwargs.get("timeout"),
        )

    return StreamableHttpTransport(f"http://test{path}", httpx_client_factory=httpx_client_factory)


async def test_fastmcp_tool_supports_starlette_inject() -> None:
    mcp = FastMCP("Demo MCP")
    mcp_app = mcp.http_app(path="/mcp")
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.starlette])
    wireup.integration.starlette.setup(container, mcp_app)

    @mcp.tool
    @inject_starlette
    async def greet(greeter: Injected[GreeterService]) -> str:
        return greeter.greet("FastMCP")

    transport = _make_transport(mcp_app)

    async with mcp_app.router.lifespan_context(mcp_app):
        async with Client(transport) as client:
            result = await asyncio.wait_for(client.call_tool("greet", {}), timeout=5)

    assert result.data == "Hello FastMCP"


async def test_fastmcp_integration_supports_http_app_without_manual_starlette_setup() -> None:
    mcp = FastMCP("Demo MCP")
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastmcp])
    wireup.integration.fastmcp.setup(container, mcp)

    @mcp.tool
    @wireup.integration.fastmcp.inject
    async def greet(greeter: Injected[GreeterService]) -> str:
        return greeter.greet("FastMCP")

    mcp_app = mcp.http_app(path="/mcp")
    transport = _make_transport(mcp_app)

    async with mcp_app.router.lifespan_context(mcp_app):
        async with Client(transport) as client:
            result = await asyncio.wait_for(client.call_tool("greet", {}), timeout=5)

    assert result.data == "Hello FastMCP"


async def test_starlette_integration_with_fastmcp_mount() -> None:
    mcp = FastMCP("MCP Test Server")

    @mcp.tool
    @inject_starlette
    async def greet(greeter: Injected[GreeterService]) -> str:
        return greeter.greet("FastMCP")

    mcp_app = mcp.http_app(path="/mcp")
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.starlette])
    app = Starlette(
        routes=[Mount("/", app=mcp_app)],
        lifespan=mcp_app.lifespan,
    )
    wireup.integration.starlette.setup(container, app)

    transport = _make_transport(app)

    async with app.router.lifespan_context(app):
        async with Client(transport) as client:
            result = await asyncio.wait_for(client.call_tool("greet", {}), timeout=5)

    assert result.data == "Hello FastMCP"


async def test_fastapi_integration_with_fastmcp_mount() -> None:
    mcp = FastMCP("MCP Test Server")

    @mcp.tool
    @inject_fastapi
    async def greet(greeter: Injected[GreeterService]) -> str:
        return greeter.greet("FastMCP")

    mcp_app = mcp.http_app(path="/mcp")
    app = FastAPI(lifespan=mcp_app.lifespan)
    app.mount("/", mcp_app)

    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])
    wireup.integration.fastapi.setup(container, app, middleware_mode=True)

    transport = _make_transport(app)

    async with app.router.lifespan_context(app):
        async with Client(transport) as client:
            result = await asyncio.wait_for(client.call_tool("greet", {}), timeout=5)

    assert result.data == "Hello FastMCP"
