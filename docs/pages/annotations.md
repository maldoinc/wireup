WireUp relies on various kind of type annotations or hints to be able to autowire dependencies.
When it is not possible to automatically locate a given dependency the argument must be annotated
with additional metadata.

## When do you need to provide annotations.

Not needed when injecting:

* Services
* Injecting an interface which has only one implementing service

Annotations required when injecting:

* Parameters
* Parameter expressions
* Injecting an interface which has multiple implementing services.

## Annotation types

Wireup supports two types of annotations. Using Python's `Annotated` or by using default values.

### Annotated

This is the preferred method for Python 3.9+ and moving forward. It is also recommended to
backport this using `typing_extensions` for Python 3.8.


```python
@container.autowire
def target(
    env: Annotated[str, Wire(param="env_name")],
    logs_cache_dir: Annotated[str, Wire(expr="${cache_dir}/logs")]
):
    ...
```

### Default values

This relies on the use of default values to inject parameters. Anything that can be passed to `Annotated` may also
be used here.

```python
@container.autowire
def target(
    env: str = wire(param="env_name"), 
    logs_cache_dir: str = wire(expr="${cache_dir}/logs")
):
    ...
```
