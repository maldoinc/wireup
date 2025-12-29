# :simple-django: Django Integration

Wireup provides seamless integration with Django through the `wireup.integration.django` module, enabling
dependency injection in Django applications.


<div class="grid cards annotate" markdown>

-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Inject dependencies in routes and automatically manage container lifecycle.


-   :material-web-check:{ .lg .middle } __Request Objects__

    ---

    Use Django request in Wireup dependencies.


-   :material-clock-fast:{ .lg .middle } __Django Settings__

    ---

    The integration exposes Django settings to Wireup as config.


-   :material-share-circle:{ .lg .middle } __Shared business logic__

    ---

    Wireup is framework-agnostic. Share the service layer between web applications and other interfaces, such as a CLI.
</div>

### Initialize the integration

Add the following to Django settings:

```python title="settings.py"
import os
from wireup.integration.django import WireupSettings

INSTALLED_APPS = [
    # ...existing code...
    "wireup.integration.django"
]

MIDDLEWARE = [
    "wireup.integration.django.wireup_middleware",
    # ...existing code...
]

WIREUP = WireupSettings(
    service_modules=["mysite.polls.services"]  # Service modules here
)

# Additional application settings
S3_BUCKET_TOKEN = os.environ["S3_BUCKET_ACCESS_TOKEN"]
```

### Inject Django settings

Django settings can be injected into services:

```python title="mysite/polls/services/s3_manager.py"
from wireup import service, Inject
from typing import Annotated

@service
class S3Manager:
    def __init__(
        self,
        # Reference configuration by name
        token: Annotated[str, Inject(config="S3_BUCKET_TOKEN")],
    ) -> None: ...

    def upload(self, file: File) -> None: ...
```

You can also use Django settings in factories:

```python title="mysite/polls/services/github_client.py"
from wireup import service
from django.conf import settings

class GithubClient:
    def __init__(self, api_key: str) -> None: ...

@service
def github_client_factory() -> GithubClient:
    return GithubClient(api_key=settings.GH_API_KEY)
```

### Inject the current request

The integration exposes the current Django request as a `scoped` lifetime dependency, which can be injected
into `scoped` or `transient` services:

```python title="mysite/polls/services/auth_service.py"
from django.http import HttpRequest
from wireup import service

@service(lifetime="scoped")
class AuthService:
    def __init__(self, request: HttpRequest) -> None:
        self.request = request
```

### Inject dependencies in views

To inject dependencies in views, simply request them by their type:

```python title="app/views.py"
from django.http import HttpRequest, HttpResponse
from mysite.polls.services import S3Manager
from wireup import Injected

def upload_file_view(
    request: HttpRequest, 
    s3_manager: Injected[S3Manager]
) -> HttpResponse:
    # Use the injected S3Manager instance
    return HttpResponse(...)
```

Class-based views are also supported. Specify dependencies in the class `__init__` function.

For more examples, see the [Wireup Django integration tests](https://github.com/maldoinc/wireup/tree/master/test/integration/django/view.py).

### Third-party Django frameworks

If your project uses third-party packages to create views, such as [Django REST framework](https://www.django-rest-framework.org/) or [Django Ninja](https://django-ninja.dev/), you must use the `@inject` decorator explicitly.

This approach should work for any Django-based framework as long as it relies on Django's `AppConfig` and middleware mechanisms.

=== "Django REST Framework"

    ```python title="app/views.py"
    from rest_framework.decorators import api_view
    from rest_framework.request import Request
    from rest_framework.response import Response
    from rest_framework.views import APIView
    from rest_framework.viewsets import ViewSet

    from wireup import Injected
    from wireup.integration.django import inject

    from mysite.polls.services import S3Manager


    @api_view(("GET",))
    @inject
    def drf_function_based_view(
        request: Request,
        s3_manager: Injected[S3Manager]
    ) -> Response:
        # Use the injected S3Manager instance
        return Response(...)


    class DRFClassBasedView(APIView):
        @inject
        def get(
            self,
            request: Request,
            s3_manager: Injected[S3Manager]
        ) -> Response:
            # Use the injected S3Manager instance
            return Response(...)


    class DRFViewSet(ViewSet):
        @inject
        def list(
            self,
            request: Request,
            s3_manager: Injected[S3Manager]
        ) -> Response:
            # Use the injected S3Manager instance
            return Response(...)
    ```

=== "Django Ninja"

    ```python title="app/views.py"
    from ninja import Router, Schema

    from wireup import Injected
    from wireup.integration.django import inject

    from mysite.polls.services import S3Manager


    router = Router()


    class ItemSchema(Schema):
        name: str
        price: float


    @router.get("/items")
    @inject
    def list_items(
        request,
        s3_manager: Injected[S3Manager]
    ):
        # Use the injected S3Manager instance
        return {"items": [...]}


    @router.post("/items")
    @inject
    def create_item(
        request,
        data: ItemSchema,
        s3_manager: Injected[S3Manager]
    ):
        # Both request body and injected service work together
        return {"name": data.name, "price": data.price}
    ```

!!! tip "Best practice for mixing core and non-core Django views"

    If your project shares core and non core-django views, consider disabling auto-injection and using `@inject`
    explicitly across all your views for consistency:

    ```python title="settings.py"
    WIREUP = WireupSettings(
        service_modules=["mysite.polls.services"],
        auto_inject_views=False,  # Disable auto-injection
    )
    ```

    === "Do"

        ```python
        # Consistent approach: use @inject everywhere
        @inject
        def core_django_view(
            request: HttpRequest,
            service: Injected[MyService]
        ) -> HttpResponse:
            return HttpResponse(...)

        @api_view(("GET",))
        @inject
        def drf_view(
            request: Request,
            service: Injected[MyService]
        ) -> Response:
            return Response(...)
        ```

    === "Don't"

        ```python
        # Inconsistent: mixing auto-injection and @inject
        def core_django_view(
            request: HttpRequest,
            service: Injected[MyService]  # Auto-injected
        ) -> HttpResponse:
            return HttpResponse(...)

        @api_view(("GET",))
        @inject  # Explicit injection
        def drf_view(
            request: Request,
            service: Injected[MyService]
        ) -> Response:
            return Response(...)
        ```

### Accessing the container

To access the Wireup container directly, use the following functions:

```python
from wireup.integration.django import get_app_container, get_request_container

# Get application-wide container
app_container = get_app_container()

# Get request-scoped container
request_container = get_request_container()
```

### Testing

For general testing tips with Wireup refer to the [test docs](../../testing.md). 
With Django you can override dependencies in the container as follows:

```python title="test_thing.py"
from wireup.integration.django import get_app_container

def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str):
            return f"Hi, {name}"

    with get_app_container().override.service(GreeterService, new=DummyGreeter()):
        res = self.client.get("/greet?name=Test")
        assert res.status_code == 200
```

!!! info "Testing async views"

    When testing async views, use Django's `AsyncClient` instead of the regular `Client`:

    ```python
    from django.test import AsyncClient
    import pytest

    @pytest.fixture
    def async_client():
        return AsyncClient()

    async def test_async_view(async_client):
        response = await async_client.get("/async-endpoint/")
        assert response.status_code == 200
    ```

### API Reference

* [django_integration](../../class/django_integration.md)
