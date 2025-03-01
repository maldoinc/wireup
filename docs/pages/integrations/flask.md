Dependency injection for Flask is available in the`wireup.integration.flask_integration` module.

**Features:**

* Automatically decorate Flask views and blueprints where the container is being used.
    * Eliminates the need for `@container.autowire` in views.
    * Views without container references will not be decorated.
* Expose Flask configuration in the container's parameters.

## Examples

```python

app = Flask(__name__)
app.config["FOO"] = "bar"

@app.get("/random")
def get_random(random: RandomService):
    return {"lucky_number": random.get_random()}

@app.get("/env")
def get_environment(
    is_debug: Annotated[bool, Inject(param="DEBUG")], 
    foo: Annotated[str, Inject(param="FOO")]
):
    return {"debug": is_debug, "foo": foo}


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

app.run()
```

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the Flask integration you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.flask import get_container

def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = self.client.get("/greet?name=Test")
```

See [Flask integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/flask/test_flask_integration.py)
for more examples.


## Api Reference

* [flask_integration](../class/flask_integration.md)
