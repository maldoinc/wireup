Dependency injection for FastAPI is available in the `wireup.integration.fastapi_integration` module.


**Features:**

* Automatically decorate Flask views and blueprints where the container is being used.
    * Eliminates the need for `@container.autowire` in views.
    * Views without container references will not be decorated.
    * Services **must** be annotated with `Inject()`.
* Can: Mix FastAPI dependencies and Wireup in views
* Can: Autowire FastAPI target with `@container.autowire`.
* Cannot: Use FastAPI dependencies in Wireup service objects.

!!! tip
    As FastAPI does not have a fixed configuration mechanism, you need to expose 
    configuration to the container. See [configuration docs](../configuration.md) for more details.

## Examples

```python title="main.py"
app = FastAPI()

@app.get("/random")
async def target(
    # Inject annotation tells wireup that this argument should be injected.
    random_service: Annotated[RandomService, Inject()],
    is_debug: Annotated[bool, Inject(param="env.debug")],

    # This is a regular FastAPI dependency.
    lucky_number: Annotated[int, Depends(get_lucky_number)]
):
    return {
        "number": random_service.get_random(), 
        "lucky_number": lucky_number,
        "is_debug": is_debug,
    }

# Initialize the integration.
# Must be called after views have been registered.
# service_modules is a list of top-level modules with service registrations.
container = wireup.create_container(
    service_modules=[services], 
    parameters=get_settings_dict()
)
wireup.integration.fastapi.setup(container, app)
```

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the FastAPI integration you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.fastapi import get_container

def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = self.client.get("/greet?name=Test")
```

See [FastAPI integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/test_fastapi_integration.py)
for more examples.

## Api Reference

* [fastapi_integration](../class/fastapi_integration.md)
