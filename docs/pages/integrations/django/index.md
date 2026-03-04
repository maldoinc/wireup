---
description: Django dependency injection with Wireup: a type-safe DI container for Django, DRF, and Ninja with setup, request/app injection patterns, testing, and troubleshooting.
---

# :simple-django: Django Integration

<div class="grid cards annotate" markdown>

- :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ______________________________________________________________________

    Inject dependencies in routes and automatically manage container lifecycle.

- :material-web-check:{ .lg .middle } __Request Objects__

    ______________________________________________________________________

    Use Django request in Wireup dependencies.

- :material-clock-fast:{ .lg .middle } __Django Settings__

    ______________________________________________________________________

    The integration exposes Django settings to Wireup as config.

- :material-share-circle:{ .lg .middle } __Shared business logic__

    ______________________________________________________________________

    Wireup is framework-agnostic. Share the service layer between web applications and other interfaces, such as a CLI.

</div>

## Quick Start

This is the shortest path to a working endpoint with explicit injection.

```python title="settings.py"
from wireup.integration.django import WireupSettings

INSTALLED_APPS = [
    # ...existing apps...
    "wireup.integration.django",
]

MIDDLEWARE = [
    "wireup.integration.django.wireup_middleware",
    # ...existing middleware...
]

WIREUP = WireupSettings(
    injectables=["mysite.services"],
    auto_inject_views=False,
)
```

```python title="mysite/services.py"
from wireup import injectable


@injectable
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello {name}"
```

```python title="mysite/views.py"
from django.http import HttpRequest, HttpResponse
from wireup import Injected
from wireup.integration.django import inject

from mysite.services import GreeterService


@inject
def greet(
    request: HttpRequest, greeter: Injected[GreeterService]
) -> HttpResponse:
    return HttpResponse(greeter.greet(request.GET.get("name", "World")))
```

```python title="mysite/urls.py"
from django.urls import path

from mysite.views import greet

urlpatterns = [
    path("greet/", greet),
]
```

Run the app with `python manage.py runserver`, then open `http://127.0.0.1:8000/greet/?name=World`.

## Detailed Guides

- [Django Setup and Installation](setup.md): installation, middleware placement, and settings/config integration.
- [Inject in Views](view_injection.md): core Django, DRF, Ninja, forms, and request-scoped patterns.
- [Request Lifecycle Patterns](request_lifecycle_patterns.md): reusable decorators, middleware-adjacent hooks, and direct container access.
- [App-Level Injection](app_injection.md): management commands, signals, checks, and scripts with `@inject_app`.
- [Django Testing](testing.md): `Client`, `AsyncClient`, `call_command`, and override patterns.
- [Troubleshooting](troubleshooting.md): common errors and quick fixes.

### API Reference

- [django_integration](../../class/django_integration.md)
