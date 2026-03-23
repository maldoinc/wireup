---
description: Django dependency injection with Wireup: a type-safe DI container for Django, DRF, and Ninja with setup, request/app injection patterns, testing, and troubleshooting.
---

# :simple-django:{.color-django} Django Integration 

<div class="grid cards annotate" markdown>

- :material-transit-connection-variant:{ .lg .middle } __Inject Beyond Views__

    ______________________________________________________________________

    Inject in core Django views, DRF handlers, Ninja endpoints, middleware helpers, decorators, and other request-time
    call sites.

    [:octicons-arrow-right-24: Learn more](request_time_injection.md)

- :material-application-braces-outline:{ .lg .middle } __App-Level Entry Points__

    ______________________________________________________________________

    Use `@inject_app` for management commands, Django 6 background tasks, signals, checks, and scripts outside request
    scope.

    [:octicons-arrow-right-24: Learn more](app_injection.md)

- :material-web-check:{ .lg .middle } __Request Context in Services__

    ______________________________________________________________________

    Inject `HttpRequest` and other scoped services into your application code without threading request objects through
    every layer.

    [:octicons-arrow-right-24: Learn more](view_injection.md)

- :material-share-circle:{ .lg .middle } __Django, DRF, and Ninja__

    ______________________________________________________________________

    Use one DI model across core Django, Django REST framework, and Django Ninja while keeping your service layer
    framework-agnostic.

</div>

Wireup integrates with Django at both request scope and application scope. Use `@inject` for request-time callables and
`@inject_app` for non-request entry points, while keeping services as ordinary Python classes that are easy to test and
reuse.

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
- [Request-Time Injection](request_time_injection.md): reusable decorators, middleware entry points, and direct container access.
- [App-Level Injection](app_injection.md): management commands, Django 6 background tasks, signals, checks, and scripts with `@inject_app`.
- [Django Testing](testing.md): `Client`, `AsyncClient`, `call_command`, and override patterns.
- [Troubleshooting](troubleshooting.md): common errors and quick fixes.

### API Reference

- [django_integration](../../class/django_integration.md)
