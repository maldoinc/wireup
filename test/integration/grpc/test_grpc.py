from collections.abc import AsyncIterator, Iterator
from concurrent import futures

import grpc
import pytest
import wireup
from wireup import Injected, injectable
from wireup.errors import WireupError
from wireup.integration.grpc import (
    WireupAsyncServerInterceptor,
    WireupServerInterceptor,
    async_servicer_context_factory,
    get_request_container,
    inject,
    inject_servicer,
    servicer_context_factory,
)

# ---------------------------------------------------------------------------
# Test Services (Singletons, Scoped Lifetimes & Teardown Trackers)
# ---------------------------------------------------------------------------


@injectable
class SingletonGreeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


@injectable(lifetime="scoped")
class LifecycleTracker:
    def __init__(self) -> None:
        self.events: list[str] = []


@injectable(lifetime="scoped")
class SyncScopedResource:
    def __init__(self, tracker: LifecycleTracker) -> None:
        self.tracker = tracker
        self.tracker.events.append("enter")


@injectable(lifetime="scoped")
def sync_scoped_with_teardown(tracker: LifecycleTracker) -> Iterator[SyncScopedResource]:
    res = SyncScopedResource(tracker)
    try:
        yield res
    finally:
        tracker.events.append("exit")


@injectable(lifetime="scoped")
async def async_scoped_with_teardown(tracker: LifecycleTracker) -> AsyncIterator[SyncScopedResource]:
    res = SyncScopedResource(tracker)
    try:
        yield res
    finally:
        tracker.events.append("exit")


@injectable(lifetime="scoped")
class SyncMetadataReader:
    def __init__(self, context: grpc.ServicerContext) -> None:
        self.metadata = dict(context.invocation_metadata())


@injectable(lifetime="scoped")
class AsyncMetadataReader:
    def __init__(self, context: grpc.aio.ServicerContext) -> None:
        self.metadata = dict(context.invocation_metadata())


class UnregisteredService:
    pass


# ---------------------------------------------------------------------------
# Helper to Register Generic RPC Handlers for a Servicer
# ---------------------------------------------------------------------------


def _register_greeter_servicer(server: grpc.Server | grpc.aio.Server, servicer: object) -> None:
    handlers = {
        "SayHello": grpc.unary_unary_rpc_method_handler(
            servicer.say_hello,  # type: ignore[attr-defined]
            request_deserializer=_decode,
            response_serializer=_encode,
        ),
        "StreamHello": grpc.unary_stream_rpc_method_handler(
            servicer.stream_hello,  # type: ignore[attr-defined]
            request_deserializer=_decode,
            response_serializer=_encode,
        ),
        "ReadMetadata": grpc.unary_unary_rpc_method_handler(
            servicer.read_metadata,  # type: ignore[attr-defined]
            request_deserializer=_decode,
            response_serializer=_encode,
        ),
    }
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler("test.Greeter", handlers),))


def _encode(value: str | bytes) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def _decode(value: bytes | str) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else value


# ---------------------------------------------------------------------------
# 1. Synchronous gRPC Server Tests (`WireupServerInterceptor`)
# ---------------------------------------------------------------------------


def test_sync_grpc_unary_stream_scoping_and_context() -> None:
    recorded_events: list[list[str]] = []

    class SyncGreeterServicer:
        def say_hello(
            self,
            request: str,
            _context: grpc.ServicerContext,
            greeter: Injected[SingletonGreeter],
            tracker: Injected[LifecycleTracker],
            _scoped: Injected[SyncScopedResource],
        ) -> str:
            tracker.events.append("handler")
            recorded_events.append(tracker.events)
            return greeter.greet(request)

        def stream_hello(
            self,
            request: str,
            _context: grpc.ServicerContext,
            greeter: Injected[SingletonGreeter],
            tracker: Injected[LifecycleTracker],
            _scoped: Injected[SyncScopedResource],
        ) -> Iterator[str]:
            recorded_events.append(tracker.events)
            for i in range(2):
                tracker.events.append(f"yield-{i}")
                yield f"{greeter.greet(request)} #{i}"

        def read_metadata(
            self,
            _request: str,
            _context: grpc.ServicerContext,
            reader: Injected[SyncMetadataReader],
        ) -> str:
            return reader.metadata.get("x-custom-header", "missing")

    container = wireup.create_sync_container(
        injectables=[
            SingletonGreeter,
            LifecycleTracker,
            sync_scoped_with_teardown,
            SyncMetadataReader,
            servicer_context_factory,
        ],
    )

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=2),
        interceptors=[WireupServerInterceptor(container)],
    )
    servicer = inject_servicer(container, SyncGreeterServicer())
    _register_greeter_servicer(server, servicer)

    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            # 1) Unary call + scoped teardown lifecycle
            unary_stub = channel.unary_unary(
                "/test.Greeter/SayHello",
                request_serializer=str.encode,
                response_deserializer=bytes.decode,
            )
            assert unary_stub("Alice") == "Hello, Alice!"
            assert recorded_events[-1] == ["enter", "handler", "exit"]

            # 2) Streaming call: scope must stay open until all items are yielded
            stream_stub = channel.unary_stream(
                "/test.Greeter/StreamHello",
                request_serializer=str.encode,
                response_deserializer=bytes.decode,
            )
            responses = list(stream_stub("Bob"))
            assert responses == ["Hello, Bob! #0", "Hello, Bob! #1"]
            assert recorded_events[-1] == ["enter", "yield-0", "yield-1", "exit"]

            # 3) ServicerContext injection
            meta_stub = channel.unary_unary(
                "/test.Greeter/ReadMetadata",
                request_serializer=str.encode,
                response_deserializer=bytes.decode,
            )
            assert meta_stub("", metadata=(("x-custom-header", "secret-token"),)) == "secret-token"
    finally:
        server.stop(grace=0)
        container.close()


# ---------------------------------------------------------------------------
# 2. Asynchronous gRPC Server Tests (`WireupAsyncServerInterceptor`)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_grpc_unary_stream_scoping_and_context() -> None:
    recorded_events: list[list[str]] = []

    class AsyncGreeterServicer:
        async def say_hello(
            self,
            request: str,
            _context: grpc.aio.ServicerContext,
            greeter: Injected[SingletonGreeter],
            tracker: Injected[LifecycleTracker],
            _scoped: Injected[SyncScopedResource],
        ) -> str:
            tracker.events.append("handler")
            recorded_events.append(tracker.events)
            return greeter.greet(request)

        async def stream_hello(
            self,
            request: str,
            _context: grpc.aio.ServicerContext,
            greeter: Injected[SingletonGreeter],
            tracker: Injected[LifecycleTracker],
            _scoped: Injected[SyncScopedResource],
        ) -> AsyncIterator[str]:
            recorded_events.append(tracker.events)
            for i in range(2):
                tracker.events.append(f"yield-{i}")
                yield f"{greeter.greet(request)} #{i}"

        @inject
        async def read_metadata(
            self,
            _request: str,
            _context: grpc.aio.ServicerContext,
            reader: Injected[AsyncMetadataReader],
        ) -> str:
            return reader.metadata.get("x-async-header", "missing")

    container = wireup.create_async_container(
        injectables=[
            SingletonGreeter,
            LifecycleTracker,
            async_scoped_with_teardown,
            AsyncMetadataReader,
            async_servicer_context_factory,
        ]
    )

    server = grpc.aio.server(interceptors=[WireupAsyncServerInterceptor(container)])
    servicer = inject_servicer(container, AsyncGreeterServicer())
    _register_greeter_servicer(server, servicer)

    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            # 1) Async Unary call + scoped teardown lifecycle
            unary_stub = channel.unary_unary(
                "/test.Greeter/SayHello",
                request_serializer=str.encode,
                response_deserializer=bytes.decode,
            )
            assert await unary_stub("Alice") == "Hello, Alice!"
            assert recorded_events[-1] == ["enter", "handler", "exit"]

            # 2) Async Streaming call: scope stays open until stream finishes
            stream_stub = channel.unary_stream(
                "/test.Greeter/StreamHello",
                request_serializer=str.encode,
                response_deserializer=bytes.decode,
            )
            responses = [item async for item in stream_stub("Bob")]
            assert responses == ["Hello, Bob! #0", "Hello, Bob! #1"]
            assert recorded_events[-1] == ["enter", "yield-0", "yield-1", "exit"]

            # 3) Async ServicerContext injection via `@inject`
            meta_stub = channel.unary_unary(
                "/test.Greeter/ReadMetadata",
                request_serializer=str.encode,
                response_deserializer=bytes.decode,
            )
            assert await meta_stub("", metadata=(("x-async-header", "async-token"),)) == "async-token"
    finally:
        await server.stop(grace=0)
        await container.close()


# ---------------------------------------------------------------------------
# 3. Startup Validation & Error Handling Tests
# ---------------------------------------------------------------------------


def test_inject_servicer_fails_fast_on_missing_dependency() -> None:
    class BrokenServicer:
        def say_hello(
            self,
            _request: str,
            _context: grpc.ServicerContext,
            _missing: Injected[UnregisteredService],
        ) -> str:
            return "never reached"

    container = wireup.create_sync_container()

    with pytest.raises(WireupError):
        inject_servicer(container, BrokenServicer())


def test_get_request_container_outside_rpc_raises_wireup_error() -> None:
    with pytest.raises(WireupError, match="Wireup request container is unavailable"):
        get_request_container()
