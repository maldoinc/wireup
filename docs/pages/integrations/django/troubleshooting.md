---
description: Troubleshoot Wireup Django integration issues including middleware setup, inject versus inject_app usage, DRF and Ninja behavior, and async context pitfalls.
---

# Django Troubleshooting

Common issues and fixes for Wireup's Django integration.

## `@inject` fails outright in request handlers

Symptom:

- Request handler injection fails immediately.
- Errors mention missing request scope or `django.http.HttpRequest ... only available during a request`.

Fix:

1. Ensure middleware is configured:

```python title="settings.py"
MIDDLEWARE = [
    "wireup.integration.django.wireup_middleware",
    # ...existing middleware...
]
```

2. Keep Wireup middleware near the start of the middleware list.
3. Use `@inject` only for request-scoped callables. For non-request callables, use `@inject_app`.

## Unknown service requested

Symptom:

- `UnknownServiceRequestedError` for a type you expected to be injectable

Fix:

1. Add the module containing the injectable to `WIREUP.injectables`.
2. Ensure the class/function is marked with `@injectable`.

```python title="settings.py"
WIREUP = WireupSettings(
    injectables=["mysite.services"],
    auto_inject_views=False,
)
```

## DRF or Ninja endpoint is not injecting

Symptom:

- Endpoint runs, but injected parameter is missing or treated as a normal arg

Fix:

- Add `@inject` explicitly on DRF/Ninja handlers.

```python
@api_view(("GET",))
@inject
def drf_view(request: Request, service: Injected[MyService]) -> Response: ...
```

## Using the wrong decorator

Rule:

- Use `@inject` for request handlers.
- Use `@inject_app` for non-request callables (commands, signals, checks, scripts).

If a callable runs outside HTTP request scope, switch from `@inject` to `@inject_app`.

## Async dependency in sync context

Symptom:

- Error indicates an async dependency cannot be created in a sync context

Fix options:

1. Use async handlers where async dependencies are injected.
2. Make the dependency sync if async behavior is not required.
3. For app-level flows, structure execution to await async work explicitly.

## Auto-injection confusion

If behavior is inconsistent between core Django and DRF/Ninja, set explicit mode:

```python title="settings.py"
WIREUP = WireupSettings(
    injectables=["mysite.services"],
    auto_inject_views=False,
)
```

Then use `@inject` explicitly in request handlers.
