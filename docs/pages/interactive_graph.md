# Interactive Graph

!!! interactive-graph "Interactive Graph"

    Turn your container into an interactive dependency graph. Explore routes, functions, services, factories,
    configuration, and scopes in a live page with search, grouping, and dependency tracing.

    Learn how it works and explore it on an demo pet store app:

    [:octicons-arrow-right-24: Live Demo](wireup_graph/pet_store.html){ .md-button .md-button--primary target="_blank" }

Wireup can render your dependency graph as an interactive page, including:

- routes and injected functions for selected frameworks
- services and factories
- configuration nodes
- singleton, scoped, and transient lifetimes

This is one of the fastest ways to understand how a real application is wired together without relying on a static dump
or a handwritten diagram.

## Preview

![Wireup interactive dependency graph demo](img/pet_store_demo.gif)


## Automatic with FastAPI and Flask

FastAPI and Flask can expose the graph page automatically at `/_wireup`.

### FastAPI

```python
from wireup.integration.fastapi import GraphEndpointOptions
import wireup.integration.fastapi

wireup.integration.fastapi.setup(
    container,
    app,
    add_graph_endpoint=True,
)
```

### Flask

```python
from wireup.integration.flask import GraphEndpointOptions
import wireup.integration.flask

wireup.integration.flask.setup(
    container,
    app,
    add_graph_endpoint=True,
)
```

## Use in other frameworks

If your framework does not have automatic graph-page setup, you can still generate the graph yourself from Python.

### 1. Build graph data

```python
from wireup.renderer.core import GraphOptions, to_graph_data

graph_data = to_graph_data(
    container,  # or get_app_container() if the integration provides it
    options=GraphOptions(base_module="myapp"),
)
```

### 2. Render it as HTML

```python
from wireup.renderer.full_page import full_page_renderer

html = full_page_renderer(graph_data, title="My App - Wireup Graph")
```

### 3. Return it from a route

```python
@app.get("/_wireup")
def wireup_graph():
    graph_data = to_graph_data(container, options=GraphOptions(base_module="myapp"))
    html = full_page_renderer(graph_data, title="My App - Wireup Graph")

    return HTMLResponse(html)
```


!!! tip
    Make sure to permission this endpoint appropriately in production since it exposes internal implementation details. You can disable it by omitting `add_graph_endpoint=True` or by not registering the route at all.
