# FastMCP Usage

Wireup provides seamless integration with FastMCP through the `wireup.integration.fastmcp` module, enabling dependency
injection in FastMCP applications.

## Standalone FastMCP

Use this when you define native FastMCP tools with `@mcp.tool`.

```python
import wireup
import wireup.integration.fastmcp
from fastmcp import FastMCP
from wireup import Injected
from wireup.integration.fastmcp import inject

mcp = FastMCP("MCP Server")


@mcp.tool
@inject
async def greet(greeter: Injected[GreeterService]) -> str:
    return greeter.greet("World")


container = wireup.create_async_container(injectables=[services])
wireup.integration.fastmcp.setup(container, mcp)

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
```

## Other FastMCP Patterns

1. `FastMCP.from_fastapi(app=app)`: integrate Wireup with FastAPI (`wireup.integration.fastapi.setup(...)`) and use `wireup.integration.fastapi.inject` on FastAPI handlers.
2. Mounted `mcp.http_app(...)` under Starlette/FastAPI: integrate Wireup with the parent framework (`wireup.integration.starlette.setup(...)` or `wireup.integration.fastapi.setup(...)`) and use that framework's `inject` decorator in mcp tools or where injection is required.

## Important

When mounting `mcp.http_app(...)` under Starlette/FastAPI, pass `lifespan=mcp_app.lifespan` to the parent app.
