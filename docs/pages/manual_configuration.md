# Manual Configuration

If you want to avoid using decorators for registration, please refer to [Automatic Registration](automatic_registration.md).

## Making Use of the Initialization Context

Given that parameters can't be resolved from type annotations alone, the `container.wire` method offers two shortcuts 
for parameter injection: `container.wire(name="")` and `container.wire(expr="")`.

To achieve the same outcome without relying on default values, you can actively employ the container's 
initialization context. This allows you to manually provide data that the library would 
otherwise gather from the decorators.

```python
container.register_all_in_module(app.services)

# Register parameters individually using add_param
container.initialization_context.add_param(
    klass=DbService,
    argument_name="connection_str",
    parameter_ref="connection_str",
)
container.initialization_context.add_param(
    klass=DbService,
    argument_name="connection_str",
    parameter_ref=TemplatedString("${cache_dir}/${USER}/db"),
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