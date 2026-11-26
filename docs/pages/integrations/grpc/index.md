# gRPC Integration

The `wireup.integration.grpc` module provides dependency injection for synchronous (`grpc.Server`) and asynchronous (`grpc.aio.Server`) gRPC applications.

<div class="grid cards annotate" markdown>

- :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ______________________________________________________________________

    Automatically manage per-RPC container scopes and inject dependencies into gRPC servicer methods.

- :material-share-circle:{ .lg .middle } __Shared Business Logic__

    ______________________________________________________________________

    Wireup is framework-agnostic, allowing the service layer to be shared across gRPC services, web applications, and CLIs.

</div>

### Setting Up the Integration

First, [create an async or sync container](../../container.md) with your dependencies:

```python
import grpc
import wireup
from wireup.integration.grpc import (
    WireupAsyncServerInterceptor,
    inject_servicer,
)

container = wireup.create_async_container(
    injectables=[services],
    config={"DEBUG": True},  # Optionally expose configuration to services
)
```

Then register `WireupAsyncServerInterceptor` (or `WireupServerInterceptor` for synchronous servers) with your gRPC server and wrap your servicer with `inject_servicer` to validate and inject dependencies at startup:

```python
server = grpc.aio.server(
    interceptors=[WireupAsyncServerInterceptor(container)],
)

servicer = inject_servicer(container, GreeterServicer())
greeter_pb2_grpc.add_GreeterServicer_to_server(servicer, server)
```

### Injecting Dependencies into Servicer Methods

Annotate servicer method parameters with `Injected[T]` or `Annotated[T, Inject(...)]`. When using `inject_servicer`, dependencies are validated at startup and injected automatically across unary and streaming RPCs. You can also apply the `@inject` decorator directly to servicer methods or helper functions.

```python title="gRPC Servicer" hl_lines="10 17"
import grpc
from wireup import Injected
from wireup.integration.grpc import inject


class GreeterServicer(greeter_pb2_grpc.GreeterServicer):
    async def SayHello(
        self,
        request: greeter_pb2.HelloRequest,
        context: grpc.aio.ServicerContext,
        greeter: Injected[GreeterService],
    ) -> greeter_pb2.HelloReply:
        return greeter_pb2.HelloReply(message=greeter.greet(request.name))

    @inject
    async def SayGoodbye(
        self,
        request: greeter_pb2.HelloRequest,
        context: grpc.aio.ServicerContext,
        greeter: Injected[GreeterService],
    ) -> greeter_pb2.HelloReply:
        return greeter_pb2.HelloReply(message=greeter.farewell(request.name))
```

### Inject gRPC ServicerContext

To inject the current `grpc.ServicerContext` or `grpc.aio.ServicerContext` in services, include the `wireup.integration.grpc` module in the injectables when [creating the container](../../container.md).

```python
container = wireup.create_async_container(
    injectables=[..., wireup.integration.grpc],
)
```

### Using gRPC ServicerContext

```python title="Example Service using gRPC ServicerContext"
import grpc
from wireup import injectable


@injectable(lifetime="scoped")
class RequestMetadata:
    def __init__(self, context: grpc.aio.ServicerContext) -> None:
        self.metadata = dict(context.invocation_metadata() or ())

    @property
    def auth_token(self) -> str | bytes | None:
        return self.metadata.get("authorization")
```

### Accessing the Container Directly

You can directly access the request-scoped Wireup container handling the current RPC using `get_request_container`:

```python
from wireup.integration.grpc import get_request_container

# Access the request-scoped container (used for the current RPC call).
# This has all the information the root container has in addition
# to data specific to the current RPC.
request_container = get_request_container()
```

### Testing

For general testing tips, see the [testing documentation](../../testing.md). To override dependencies in the container during tests, use `container.override`:

```python title="test_grpc.py"
class UppercaseGreeter(GreeterService):
    def greet(self, name: str) -> str:
        return super().greet(name).upper()


async def test_override() -> None:
    with container.override({GreeterService: UppercaseGreeter()}):
        response = await stub.SayHello(greeter_pb2.HelloRequest(name="world"))

    assert response.message == "HELLO WORLD"
```

For more examples, see the
[gRPC integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/grpc/test_grpc_integration.py).

### Lifecycle Management

`WireupAsyncServerInterceptor` and `WireupServerInterceptor` automatically enter a scoped container when an RPC call starts and close it once the unary response returns or the response stream completes. Remember to close the root container (`await container.close()` or `container.close()`) when shutting down your gRPC server.

### API Reference

- [grpc_integration](../../class/grpc_integration.md)
