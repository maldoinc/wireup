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


container = wireup.create_container(
    # service_modules a list of top-level modules where your services reside.
    service_modules=[services],
    parameters={"FOO": "bar"}
)

# Initialize the integration.
# Must be called after views and configuration have been added.
wireup.integration.flask.setup(container, app, import_flask_config=True)

app.run()
```

## Api Reference

* [flask_integration](../class/flask_integration.md)
* [ParameterEnum](../class/parameter_enum.md)
