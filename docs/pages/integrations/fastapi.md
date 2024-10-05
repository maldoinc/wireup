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
# Pass to service_modules a list of top-level modules where your services reside.
container = wireup.create_container(
    service_modules=[services], 
    parameters=get_settings_dict()
)
wireup.integration.setup(FastApiIntegration(container, app))
```

## Api Reference

* [fastapi_integration](../class/fastapi_integration.md)
