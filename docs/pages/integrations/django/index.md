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

    The integration exposes Django settings to Wireup as parameters.


-   :material-ninja:{ .lg .middle } __Django Ninja Support__

    ---

    Use `@inject` from `wireup.integration.django.ninja` for seamless injection in Django Ninja routes.

    [:octicons-arrow-right-24: Learn more](#django-ninja)


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
        token: Annotated[str, Inject(param="S3_BUCKET_TOKEN")],
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

### Django Ninja

[Django Ninja](https://django-ninja.dev/) is a FastAPI-inspired web framework for Django. 
Wireup provides a dedicated `@inject` decorator for Django Ninja routes because Ninja inspects 
function signatures to determine request parameters (Body, Query, Path, etc.).

Without the decorator, Wireup-annotated parameters would be incorrectly interpreted as request 
parameters, causing Pydantic schema generation errors.

#### Usage

```python title="mysite/api/views.py"
from ninja import Router, Schema
from wireup import Injected
from wireup.integration.django.ninja import inject

from mysite.services import ItemService

class ItemSchema(Schema):
    name: str
    price: float

router = Router()

@router.post("/items/")
@inject  # Place below @router.* decorators
def create_item(
    request,
    data: ItemSchema,  # Ninja parses this as Body
    service: Injected[ItemService],  # Wireup injects this
):
    return service.create(data)
```

The `@inject` decorator:

1. Hides Wireup-injectable parameters from Django Ninja's signature inspection
2. Resolves dependencies from the Wireup container at request time

!!! warning "Decorator order"
    Place `@inject` **below** `@router.*` decorators:
    
    ```python
    @router.get("/items/")  # Router decorator first
    @inject                  # Inject decorator second
    def list_items(request, service: Injected[ItemService]):
        ...
    ```

#### Injecting parameters

You can also inject configuration parameters:

```python
from typing import Annotated
from wireup import Inject, Injected
from wireup.integration.django.ninja import inject

@router.get("/config/")
@inject
def get_config(
    request,
    debug: Annotated[bool, Inject(param="DEBUG")],
    service: Injected[ConfigService],
):
    return {"debug": debug, "config": service.get_all()}
```

For more examples, see the [Django Ninja integration tests](https://github.com/maldoinc/wireup/tree/master/test/integration/django_ninja/).

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

### API Reference

* [django_integration](../../class/django_integration.md)
