# Manual Configuration

WireUp provides convenient decorators and functions for you to use and perform dependency injection.
If using decorators or functions such as `wire` not appropriate for your application then manual container
configuration is also possible.

To eliminate usage of decorators for registration, please refer to [Automatic Registration](automatic_registration.md).

## Making Use of the Initialization Context

Given that parameters can't be resolved from type annotations alone, the `container.wire` method offers two shortcuts 
for parameter injection: `wire(name="")` and `wire(expr="")`.

To achieve the same outcome without relying on default values, you can use the container's 
initialization context. This allows you to manually provide data that the library would 
otherwise gather from the decorators.

```python
container.register_all_in_module(app.services, "*Service")

# Register parameters individually using add_param
container.initialization_context.add_param(
    klass=DbService,
    argument_name="connection_str",
    parameter_ref="connection_str",
)
container.initialization_context.add_param(
    klass=DbService,
    argument_name="connection_str",
    parameter_ref=TemplatedString("${cache_dir}/${auth_user}/db"),
)

# Alternatively, you can update the context in bulk using a dictionary of initializer parameter names as keys
# and container parameter references as values.
# When using interpolated strings, make sure you wrap the string with TemplatedString.

# NOTE: Parameter references MUST be wrapped with ParameterWrapper here!
container.initialization_context.update(
    DbService,
    {
        "connection_str": "connection_str",
        "cache_dir": TemplatedString("${cache_dir}/${USER}/db"),
    },
)
```

Configuration can also be stored in JSON or YAML documents that can be read and used to update the container accordingly.