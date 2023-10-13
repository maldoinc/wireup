WireUp provides convenient decorators and functions for you to use and perform dependency injection.
If using decorators or functions such as `wire` not appropriate for your application then manual container
configuration is also possible.

## Using wireup without registration decorators

In addition to using `@container.register` to register each dependency, automatic registration is also possible by
using the `container.regiter_all_in_module(module, pattern = "*")` method.

Module represents the top level module containing all your dependencies, optionally a `fnmatch` pattern can be specified
to only register classes that match the pattern. This is the equivalent of using `@container.register`
on each.

```python
container.register_all_in_module(app.service, "*Service")
```

## Interfaces

Even though It's not possible to automatically register abstract types and implementation using qualifiers. 
Manual registration is still possible.

```python
container.abstract(FooBase)
container.register(FooBar, qualifier="bar")
container.register(FooBaz, qualifier="baz")
```

## Manually wiring parameters

Given that parameters can't be resolved from type annotations alone, they must be annotated.

To achieve the same outcome without relying on annotations, you can use the container's 
initialization context. This allows you to manually provide data that the library would 
otherwise gather from the decorators or annotations.

```python
container.register_all_in_module(app.services, "*Service")

# Register parameters individually using add_param
container.context.add_dependency(
    klass=DbService,
    argument_name="connection_str",
    value=AnnotatedParameter(annotation=ParameterWrapper("connection_str")),
)
container.context.put_param(
    klass=DbService,
    argument_name="connection_str",
    value=AnnotatedParameter(
        annotation=ParameterWrapper(TemplatedString("${cache_dir}/${auth_user}/db"))
    ),
)
```
Configuration can also be stored in JSON or YAML documents that can be read and used to update the container accordingly.


## Manually wiring services

The context's `put` method will register a new dependency for a particular service type.

!!! tip
    Make sure to call `context.init` on the class to initialize the registration before calling `put`.

```python
self.context.init_target(MyService)
self.context.add_dependency(MyService, "foo", AnnotatedParameter(klass=DbService))
```


