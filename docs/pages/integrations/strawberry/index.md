# Strawberry Integration

Wireup does not provide a dedicated Strawberry runtime integration module. Instead, use the Wireup integration for the
framework Strawberry is running on.

### Setup

=== "Starlette"

    ```python
    import strawberry
    import wireup
    import wireup.integration.starlette
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from strawberry.asgi import GraphQL

    @strawberry.type
    class Query:
        ...

    container = wireup.create_async_container(
        injectables=[services, wireup.integration.starlette],
    )
    schema = strawberry.Schema(query=Query)
    app = Starlette(routes=[Mount("/", app=GraphQL(schema))])
    wireup.integration.starlette.setup(container, app)
    ```

=== "FastAPI"

    ```python
    import strawberry
    import wireup
    import wireup.integration.fastapi
    from fastapi import FastAPI
    from strawberry.fastapi import GraphQLRouter

    @strawberry.type
    class Query:
        ...

    container = wireup.create_async_container(
        injectables=[services, wireup.integration.fastapi],
    )
    schema = strawberry.Schema(query=Query)
    app = FastAPI()
    app.include_router(GraphQLRouter(schema), prefix="/graphql")
    # middleware_mode=True is required for Strawberry resolvers using @inject.
    wireup.integration.fastapi.setup(container, app, middleware_mode=True)
    ```

=== "Django"

    Follow the [Django Integration](../django/index.md) guide for setup (`INSTALLED_APPS`, `WIREUP`, `wireup_middleware`)
    and then mount Strawberry's Django view:

    ```python
    import strawberry
    from django.urls import path
    from strawberry.django.views import GraphQLView

    @strawberry.type
    class Query:
        ...

    schema = strawberry.Schema(query=Query)
    urlpatterns = [
        path("graphql", GraphQLView.as_view(schema=schema)),
    ]
    ```

### Inject Decorator + HTTP Request

=== "Starlette"

    ```python
    import strawberry
    from starlette.requests import Request
    from wireup import Injected, injectable
    from wireup.integration.starlette import inject

    from my_app.services import GreeterService


    @injectable(lifetime="scoped")
    class RequestContext:
        def __init__(self, request: Request):
            self.request = request


    @strawberry.type
    class Query:
        @strawberry.field
        @inject
        def hello(self, greeter: Injected[GreeterService]) -> str:
            return greeter.greet("World")

        @strawberry.field
        @inject
        def user_agent(self, ctx: Injected[RequestContext]) -> str:
            return ctx.request.headers.get("user-agent", "unknown")
    ```

=== "FastAPI"

    ```python
    import strawberry
    from fastapi import Request
    from wireup import Injected, injectable
    from wireup.integration.fastapi import inject

    from my_app.services import GreeterService


    @injectable(lifetime="scoped")
    class RequestContext:
        def __init__(self, request: Request):
            self.request = request


    @strawberry.type
    class Query:
        @strawberry.field
        @inject
        def hello(self, greeter: Injected[GreeterService]) -> str:
            return greeter.greet("World")

        @strawberry.field
        @inject
        def user_agent(self, ctx: Injected[RequestContext]) -> str:
            return ctx.request.headers.get("user-agent", "unknown")
    ```

=== "Django"

    ```python
    import strawberry
    from django.http import HttpRequest
    from wireup import Injected, injectable
    from wireup.integration.django import inject

    from my_app.services import GreeterService


    @injectable(lifetime="scoped")
    class RequestContext:
        def __init__(self, request: HttpRequest):
            self.request = request


    @strawberry.type
    class Query:
        @strawberry.field
        @inject
        def hello(self, greeter: Injected[GreeterService]) -> str:
            return greeter.greet("World")

        @strawberry.field
        @inject
        def user_agent(self, ctx: Injected[RequestContext]) -> str:
            return ctx.request.headers.get("User-Agent", "unknown")
    ```
