---
description: Wireup interactive dependency graph for Django: expose the graph page, understand what it shows, and gate it by environment.
---

## Enable The Interactive Graph

Create a small view that renders the graph page from the application container:

```python title="mysite/wireup_graph.py"
from django.http import HttpRequest, HttpResponse
from wireup.integration.django import get_app_container
from wireup.renderer.full_page import GraphEndpointOptions, render_graph_page


def wireup_graph(_request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        render_graph_page(
            get_app_container(),
            title="My Django App - Wireup Graph",
            options=GraphEndpointOptions(base_module="mysite"),
        ),
        content_type="text/html",
    )
```

Then mount it in your URLconf:

```python title="mysite/urls.py"
from django.conf import settings
from django.urls import path

from mysite.wireup_graph import wireup_graph

urlpatterns = [
    # ...your existing routes...
]

if settings.DEBUG:
    urlpatterns.append(path("_wireup", wireup_graph))
```

Then open `http://127.0.0.1:8000/_wireup`.

## What It Shows

The graph can include:

- services and factories
- configuration nodes
- singleton, scoped, and transient lifetimes
- discovered Django consumers that the graph can infer from the loaded app state

## Environment Gating

Because the graph exposes internal implementation details, it is best treated as a development tool.

A typical pattern is to mount the route only in local or non-production environments:

```python title="mysite/urls.py"
if settings.DEBUG:
    urlpatterns.append(path("_wireup", wireup_graph))
```

If you need stricter control, omit the route entirely in production or protect it like any other internal debug page.

## Related

- [Django Integration](index.md)
- [General Interactive Graph Docs](../../interactive_graph.md)
- [Django Request-Time Injection](request_time_injection.md)
