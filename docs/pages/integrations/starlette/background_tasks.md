# Background Tasks

Use `WireupTask` when you want Wireup to resolve dependencies inside a Starlette background task callback.

## Usage

1. Define your task function with `Injected[...]` parameters for any Wireup dependencies
1. Inject `WireupTask` in your route handler: `wireup_task: Injected[WireupTask]`
1. Wrap the task function before scheduling: `wireup_task(write_greeting)`
1. Schedule the task as usual with the wrapped callable and any non-Wireup task arguments

This keeps Starlette's normal background-task API while enabling Wireup injection in the scheduled callback.

## Scope Behavior

Each background task runs in its own Wireup scope. Singletons are shared with the rest of the application as usual, but
scoped and transient dependencies, like DB sessions or transactions, are created fresh for the task and torn down when
it completes.

## Example

```python
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from wireup import Injected
from wireup.integration.starlette import WireupTask, inject
from myapp.services import GreeterService


def write_greeting(name: str, greeter: Injected[GreeterService]) -> None:
    print(greeter.greet(name))


@inject
async def hello(
    request: Request,
    wireup_task: Injected[WireupTask],
) -> PlainTextResponse:
    name = request.query_params.get("name", "World")

    return PlainTextResponse(
        "ok",
        background=BackgroundTask(wireup_task(write_greeting), name),
    )
```
