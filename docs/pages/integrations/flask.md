Dependency injection for Flask is available in the `wireup.integration.flask` module.

**Features:**

- [x] Dependency injection in function-based and class-based views (sync and async)
- [x] Request-scoped container lifecycle management.

---

### Initialize the integration

To initialize the integration, call `wireup.integration.flask.setup` after adding all views and configuration.

```python
from wireup import Inject, Injected, service

app = Flask(__name__)
app.config["FOO"] = "bar"

container = wireup.create_sync_container(
    # service_modules is a list of top-level modules with service registrations.
    service_modules=[services],
    parameters={
        **app.config, # Optionally expose flask configuration to the container.
        "FOO": "bar"
    }
)

# Initialize the integration.
# Must be called after views and configuration have been added.
wireup.integration.flask.setup(container, app)
```

### Inject in Flask Views

To inject dependencies, add the type to the views' signature and annotate them as necessary.
See [Annotations](../annotations.md) for more details.

```python title="Flask View"
@app.get("/random")
def get_random(random: Injected[RandomService]):
    return {"lucky_number": random.get_random()}

@app.get("/env")
def get_environment(
    is_debug: Annotated[bool, Inject(param="DEBUG")], 
    foo: Annotated[str, Inject(param="FOO")]
):
    return {"debug": is_debug, "foo": foo}
```

### Accessing the Container

If you ever need to access the Wireup container directly, use the provided functions:

```python
from wireup.integration.flask import get_app_container, get_request_container

# Get application-wide container
app_container = get_app_container(app)

# Get request-scoped container
request_container = get_request_container()
```

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the Flask integration, you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.flask import get_app_container

def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = self.client.get("/greet?name=Test")
```

See [Flask integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/flask/test_flask_integration.py)
for more examples.

## API Reference

* [flask_integration](../class/flask_integration.md)
