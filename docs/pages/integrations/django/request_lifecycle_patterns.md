# Request Lifecycle Patterns

Wireup injection in Django is not limited to views. You can also inject services in request-time helpers such as custom
decorators and middleware-adjacent functions.

## Composable Request Decorators

Use `@inject` to build reusable decorators that run inside the request lifecycle.

```python
from functools import wraps
from django.http import HttpRequest, HttpResponseForbidden
from wireup import Injected
from wireup.integration.django import inject

from myapp.services import BillingService


def require_plan(plan: str):
    def decorator(view_fn):
        @wraps(view_fn)
        @inject
        def wrapped(
            request: HttpRequest,
            *args,
            billing: Injected[BillingService],
            **kwargs,
        ):
            if not billing.has_plan(request.user.id, plan):
                return HttpResponseForbidden("Upgrade required")
            return view_fn(request, *args, **kwargs)

        return wrapped

    return decorator
```

```python
@require_plan("pro")
def analytics_view(request: HttpRequest): ...
```

!!! note

    The `require_plan` example above is sync-only. If your target view is async, use an async decorator variant and
    `await` the wrapped view function.

## Middleware-Adjacent Request Hooks

Django middleware itself does not use Django's view signature injection. For request-time middleware hooks, call
helpers that use `@inject` or direct request-container access.

```python
from django.http import HttpRequest
from wireup import Injected
from wireup.integration.django import inject

from myapp.services import RequestContextService


@inject
def initialize_request_context(
    request: HttpRequest,
    context_service: Injected[RequestContextService],
) -> None:
    context_service.initialize(request)
```

```python
class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        initialize_request_context(request)
        return self.get_response(request)
```

!!! warning

    Ensure `wireup.integration.django.wireup_middleware` appears before middleware that calls injected helpers.
    Otherwise request-scoped injection is not available yet.

## Direct Container Access

When needed, access containers directly:

```python
from wireup.integration.django import get_app_container, get_request_container

# Current request-scoped container (available only during a request)
request_container = get_request_container()

# Application-wide container
app_container = get_app_container()
```

Prefer `@inject` for request-time helpers and `@inject_app` for non-request entry points.

## Testing Lifecycle Helpers

See [Django Testing](testing.md) for endpoint tests and dependency overrides. These patterns are tested the same way:

- call endpoints with `Client` or `AsyncClient`
- use `get_app_container().override.injectable(...)` to inject fakes
