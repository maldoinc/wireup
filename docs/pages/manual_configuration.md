Wireup provides convenient decorators and functions for you to use and configure service objects.
If using them is not appropriate for the project, or you want to keep service objects free of wireup imports,
manual configuration is also possible.

## Using factory functions

With this method you keep service objects free of any annotations and instead use factory functions to create them.
The function requests any dependencies necessary to create the service and instantiates it.

```python
# service/translator.py
@dataclass
class TranslatorService:
    default_locale: str

# service/greeter.py
@dataclass
class GreeterService:
    translator: TranslatorService


# service/factories.py
# Factory functions will have to be registered and use annotations as usual.
@container.register
def translator_factory(
    default_locale: Annotated[str, Wire(param="default_locale")],
) -> TranslatorService:
    return TranslatorService(default_locale)


@container.register
def greeter_factory(translator: TranslatorService) -> GreeterService:
    return GreeterService(translator)
```

## Using initialization context

In addition to using `@container.register` to register each dependency, automatic registration is also possible by
using the `wireup.register_all_in_module` method. You can use this to import any classes that match a `fnmatch` pattern
or a regular expression.

Module represents the top level module containing all your dependencies, optionally a `fnmatch` pattern can be specified
to only register classes that match the pattern. This is the equivalent of using `@container.register`
on each.

```python
wireup.register_all_in_module(app.service, "*Service")
```

!!! tip
    Register services either using `register_all_in_module` or by calling `container.register` on each.
    Doing so will automatically discover all non-parameter dependencies.

### Interfaces

Even though It's not possible to automatically register abstract types and implementation using qualifiers. 
Manual registration is still possible.

```python
container.abstract(FooBase)
container.register(FooBar, qualifier="bar")
container.register(FooBaz, qualifier="baz")
```

### Manually wiring parameters

Given that parameters can't be resolved from type annotations alone, they must be annotated.

To achieve the same outcome without relying on annotations, you can use the container's 
initialization context. This allows you to manually provide data that the library would 
otherwise gather from the decorators or annotations.


```python
wireup.register_all_in_module(app.services, "*Service")

# Register parameters individually using add_dependency
container.context.add_dependency(
    klass=DbService,
    argument_name="connection_str",
    value=AnnotatedParameter(annotation=ParameterWrapper("connection_str")),
)
container.context.add_dependency(
    klass=DbService,
    argument_name="connection_str",
    value=AnnotatedParameter(
        annotation=ParameterWrapper(TemplatedString("${cache_dir}/${auth_user}/db"))
    ),
)
```
Configuration can also be stored in JSON or YAML documents that can be read and used to update the container accordingly.
