Dependency injection for FastAPI (all versions) is available via the first-party integration wireup provides, available in
`wireup.integration.fastapi_integration`.


**Features:**

* Automatically decorate Flask views and blueprints where the container is being used.
    * Eliminates the need for `@container.autowire` in views.
    * Views without container references will not be decorated.
    * Services **must** be annotated with `Wire()`.
* Can: Mix FastAPI dependencies and Wireup in views
* Can: Autowire FastAPI target with `@container.autowire`.
* Cannot: Use FastAPI dependencies in Wireup service objects.

!!! tip
    As FastAPI does not have a fixed configuration mechanism, you need to expose 
    configuration to the container. See [configuration docs](../configuration.md).

## Examples

```python

app = FastAPI()

@app.get("/random")
async def target(
    # Wire annotation tells wireup that this argument should be injected.
    random_service: Annotated[RandomService, Wire()],
    is_debug: Annotated[bool, Wire(param="env.debug")],

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
wireup_init_fastapi_integration(app, service_modules=[services])
```

## Api Reference

* [fastapi_integration](../class/fastapi_integration.md)
