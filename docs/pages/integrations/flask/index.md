# :simple-flask: Flask Integration

Dependency injection for Flask is available in the `wireup.integration.flask` module.

<div class="grid cards annotate" markdown>

- :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ______________________________________________________________________

    Inject dependencies in routes and automatically manage container lifecycle.

- :material-share-circle:{ .lg .middle } __Shared business logic__

    ______________________________________________________________________

    Wireup is framework-agnostic. Share the service layer between web applications and other interfaces, such as a CLI.

</div>

!!! interactive-graph "Interactive Graph"

    Turn your container into an interactive dependency graph. Explore routes, functions, services, factories,
    configuration, and scopes in a live page with search, grouping, and dependency tracing.

    Learn how it works and explore it on an demo pet store app:

    [Documentation](interactive_graph.md){ .md-button target="_blank" }
    [:octicons-arrow-right-24: Live Demo](wireup_graph/pet_store.html){ .md-button .md-button--primary target="_blank" }

### Initialize the integration

First, [create a sync container](../../container.md) with your dependencies:

```python
from flask import Flask
from wireup import Inject, Injected, injectable

app = Flask(__name__)
app.config["FOO"] = "bar"

container = wireup.create_sync_container(
    injectables=[services],
    config={
        **app.config,  # Optionally expose flask configuration to the container
        "API_KEY": "secret",
    },
)
```

Then initialize the integration by calling `wireup.integration.flask.setup` after adding all views and configuration:

```python
# Initialize the integration.
# Must be called after views and configuration have been added.
wireup.integration.flask.setup(container, app)
```

To expose the interactive dependency graph page at `/_wireup`, enable the graph endpoint during setup:

```python
from wireup.integration.flask import GraphEndpointOptions

wireup.integration.flask.setup(
    container,
    app,
    add_graph_endpoint=True,
)
```

### Inject in Flask Views

To inject dependencies, add the type to the view's signature and annotate with `Injected[T]` or
`Annotated[T, Inject(...)]`.

```python title="Flask View"
@app.get("/random")
def get_random(random: Injected[RandomService]):
    return {"lucky_number": random.get_random()}


@app.get("/env")
def get_environment(
    is_debug: Annotated[bool, Inject(config="DEBUG")],
    foo: Annotated[str, Inject(config="FOO")],
):
    return {"debug": is_debug, "foo": foo}
```

### Accessing the Container

To access the Wireup container directly, use the following functions:

```python
from wireup.integration.flask import get_app_container, get_request_container

# Get application-wide container
app_container = get_app_container(app)

# Get request-scoped container
request_container = get_request_container()
```

### Testing

For general testing tips with Wireup refer to the [test docs](../../testing.md). With the Flask integration, you can
override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.flask import get_app_container


def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.injectable(
        GreeterService,
        new=DummyGreeter(),
    ):
        res = self.client.get("/greet?name=Test")
```

See
[Flask integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/flask/test_flask_integration.py)
for more examples.

### Dependency Validation

`wireup.integration.flask.setup(...)` validates the views it wraps up front.
Missing dependencies and config values fail during setup.

See [What Wireup Validates](../../what_wireup_validates.md) for the full rules.

### API Reference

- [flask_integration](../../class/flask_integration.md)
