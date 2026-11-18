import functools
import inspect
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

import grpc

from wireup import inject_from_container
from wireup._annotations import injectable
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer, SyncContainer
from wireup.ioc.util import get_inject_annotated_parameters, is_wireup_injected

__all__ = [
    "WireupAsyncServerInterceptor",
    "WireupServerInterceptor",
    "async_servicer_context_factory",
    "get_request_container",
    "inject",
    "inject_servicer",
    "servicer_context_factory",
]


request_container: ContextVar[ScopedSyncContainer | ScopedAsyncContainer] = ContextVar("wireup_grpc_scoped_container")


@injectable(lifetime="scoped")
def servicer_context_factory() -> grpc.ServicerContext:
    """Provide the current sync gRPC ServicerContext as a dependency."""
    msg = "ServicerContext in Wireup is only available during an active RPC call."
    raise WireupError(msg)


@injectable(lifetime="scoped")
def async_servicer_context_factory() -> grpc.aio.ServicerContext:
    """Provide the current async gRPC ServicerContext as a dependency."""
    msg = "aio.ServicerContext in Wireup is only available during an active RPC call."
    raise WireupError(msg)


class WireupAsyncServerInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, container: AsyncContainer) -> None:
        self.container = container

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        return _wrap_rpc_method_handler(
            handler,
            functools.partial(_wrap_async_unary, self.container),
            functools.partial(_wrap_async_stream, self.container),
        )


class WireupServerInterceptor(grpc.ServerInterceptor):
    def __init__(self, container: SyncContainer) -> None:
        self.container = container

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = continuation(handler_call_details)
        if handler is None:
            return None

        return _wrap_rpc_method_handler(
            handler,
            functools.partial(_wrap_sync_unary, self.container),
            functools.partial(_wrap_sync_stream, self.container),
        )


def _wrap_async_unary(container: AsyncContainer, fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    async def wrapper(request_or_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
        async with container.enter_scope({grpc.aio.ServicerContext: context}) as scoped:
            token = request_container.set(scoped)
            try:
                return await fn(request_or_iterator, context)
            finally:
                request_container.reset(token)

    return wrapper


def _wrap_async_stream(container: AsyncContainer, fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    async def wrapper(request_or_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
        async with container.enter_scope({grpc.aio.ServicerContext: context}) as scoped:
            token = request_container.set(scoped)
            try:
                stream = fn(request_or_iterator, context)
                if inspect.iscoroutine(stream):
                    stream = await stream
                async for response in stream:
                    yield response
            finally:
                request_container.reset(token)

    return wrapper


def _wrap_sync_unary(container: SyncContainer, fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(request_or_iterator: Any, context: grpc.ServicerContext) -> Any:
        with container.enter_scope({grpc.ServicerContext: context}) as scoped:
            token = request_container.set(scoped)
            try:
                return fn(request_or_iterator, context)
            finally:
                request_container.reset(token)

    return wrapper


def _wrap_sync_stream(container: SyncContainer, fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(request_or_iterator: Any, context: grpc.ServicerContext) -> Any:
        with container.enter_scope({grpc.ServicerContext: context}) as scoped:
            token = request_container.set(scoped)
            try:
                yield from fn(request_or_iterator, context)
            finally:
                request_container.reset(token)

    return wrapper


def _wrap_rpc_method_handler(
    handler: grpc.RpcMethodHandler,
    wrap_unary: Callable[[Callable[..., Any]], Callable[..., Any]],
    wrap_stream: Callable[[Callable[..., Any]], Callable[..., Any]],
) -> grpc.RpcMethodHandler:
    if handler.unary_unary:
        return grpc.unary_unary_rpc_method_handler(
            wrap_unary(handler.unary_unary),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    if handler.unary_stream:
        return grpc.unary_stream_rpc_method_handler(
            wrap_stream(handler.unary_stream),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    if handler.stream_unary:
        return grpc.stream_unary_rpc_method_handler(
            wrap_unary(handler.stream_unary),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    if handler.stream_stream:
        return grpc.stream_stream_rpc_method_handler(
            wrap_stream(handler.stream_stream),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    return handler


def inject_servicer(
    container: SyncContainer | AsyncContainer,
    servicer: Any,
) -> Any:
    """Wrap all RPC methods on a gRPC servicer that use `Injected[T]` and validate them at startup."""
    for name, method in inspect.getmembers(servicer, predicate=inspect.ismethod):
        if name.startswith("_") or is_wireup_injected(method):
            continue

        if not get_inject_annotated_parameters(method):
            continue

        wrapped = inject_from_container(container, get_request_container)(method)
        setattr(servicer, name, wrapped)

    return servicer


def get_request_container() -> ScopedSyncContainer | ScopedAsyncContainer:
    """Return the scoped container handling the current gRPC call."""
    try:
        return request_container.get()
    except (LookupError, AttributeError) as e:
        msg = (
            "Wireup request container is unavailable in the current execution context.\n"
            "Ensure WireupServerInterceptor (or WireupAsyncServerInterceptor) is registered "
            "with your gRPC server."
        )
        raise WireupError(msg) from e


inject = inject_from_container_unchecked(get_request_container, hide_annotated_names=True)
"""Inject dependencies into gRPC servicer methods. Decorate your RPC methods with this
and use `Injected[T]` or `Annotated[T, Inject()]` to specify dependencies.
"""
