# Manual configuration

To avoid using decorators see [Automatic Registration](automatic_registration.md).


## Using the initialization context

Since parameter injection cannot be inferred from typing alone the `container.wire` method has two 
shortcuts to inject parameters: `container.wire(name="")` and `container.wire(expr="")`. 

To achieve the same effect without having to rely on the default value you can use the container's 
initialization context. This manually provides data the library would have otherwise picked up using the decorators.


```python
container.register_all_in_module(app.services)

# Register parameters one by one using add_param
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


# Alternatively you can update the context in bulk using a dict of initializer parameter name as keys
# and container parameter reference as values. 
# To use interpolated strings you must wrap the string with TemplatedString.

# NOTE: Parameter references MUST be wrapped with ParameterWrapper here!
container.initialization_context.update(
    DbService,
    {
        "connection_str": "connection_str",
        "cache_dir": TemplatedString("${cache_dir}/${USER}/db"),
    },
)
```

To use it you must populate the context manually with information for a particular service.
Configuration can also be stored in json/yaml documents which you can read and update the container accordingly.