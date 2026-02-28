from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup.integration.starlette import get_app_container, get_request_container
from wireup.integration.starlette import inject as starlette_inject
from wireup.integration.starlette import setup as setup_starlette

if TYPE_CHECKING:
    from wireup.ioc.container.async_container import AsyncContainer

__all__ = ["get_app_container", "get_request_container", "inject", "setup"]


def setup(container: AsyncContainer, mcp: Any) -> None:
    """Integrate Wireup with a FastMCP instance."""
    if not hasattr(mcp, "http_app"):
        msg = "Expected a FastMCP instance with an 'http_app' method."
        raise TypeError(msg)

    original_http_app = mcp.http_app

    if getattr(original_http_app, "__wireup_fastmcp_wrapped__", False):
        return

    def wrapped_http_app(*args: Any, **kwargs: Any) -> Any:
        app = original_http_app(*args, **kwargs)
        if not hasattr(app.state, "wireup_container"):
            setup_starlette(container, app)
        return app

    wrapped_http_app.__wireup_fastmcp_wrapped__ = True  # type: ignore[attr-defined]
    mcp.http_app = wrapped_http_app


inject = starlette_inject
"""Inject dependencies into FastMCP tools running over HTTP transports.
"""
