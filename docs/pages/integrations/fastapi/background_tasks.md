# Background Tasks

Use `WireupTask` when you want Wireup to resolve dependencies inside a FastAPI background task callback.

## Usage

1. Define your task function with `Injected[...]` parameters for any Wireup dependencies
2. Inject `WireupTask` in your route handler: `wireup_task: Injected[WireupTask]`
3. Wrap the task function before scheduling: `wireup_task(write_greeting)`
4. Schedule the task as usual with the wrapped callable and any non-Wireup task arguments

This keeps FastAPI's normal background-task API while enabling Wireup injection in the scheduled callback.


## Scope Behavior

Each background task runs in its own Wireup scope. 
Singletons are shared with the rest of the application as usual, but scoped and transient dependencies, 
like DB sessions or transactions, are created fresh for the task and torn down when it completes. 


=== "Use with `BackgroundTasks`"

    ```python
    from fastapi import BackgroundTasks, FastAPI
    from wireup import Injected
    from wireup.integration.fastapi import WireupTask
    from myapp.services import GreeterService

    app = FastAPI()


    def write_greeting(name: str, greeter: Injected[GreeterService]) -> None:
        print(greeter.greet(name))


    @app.get("/")
    async def hello(tasks: BackgroundTasks, wireup_task: Injected[WireupTask]):
        tasks.add_task(wireup_task(write_greeting), "World")
        return {"ok": True}
    ```


=== "Use with `Response(background=...)`"

    ```python
    from fastapi import FastAPI
    from starlette.background import BackgroundTask
    from starlette.responses import PlainTextResponse
    from wireup import Injected
    from wireup.integration.fastapi import WireupTask
    from myapp.services import GreeterService

    app = FastAPI()


    def write_greeting(name: str, greeter: Injected[GreeterService]) -> None:
        print(greeter.greet(name))


    @app.get("/")
    async def hello(wireup_task: Injected[WireupTask]) -> PlainTextResponse:
        return PlainTextResponse(
            "ok",
            background=BackgroundTask(wireup_task(write_greeting), "World"),
        )
    ```

