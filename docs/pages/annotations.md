Autowiring relies on annotations or hints to be able to inject dependencies.
When it is not possible to automatically locate a given dependency the argument must be annotated
with additional metadata.

!!! note
    Although using annotations is recommended, they are entirely optional.
    For more info see: [Manual Configuration](manual_configuration.md).

## When do you need to provide annotations.

| Injecting                               | Annotations required? | What is required     |
|-----------------------------------------|-----------------------|----------------------|
| Services                                | No                    |                      |
| Interface with only one implementation  | No                    |                      |
| Interface with multiple implementations | Yes                   | Qualifier            |
| Parameters                              | Yes                   | Parameter name       |
| Parameter expressions                   | Yes                   | Parameter expression |
 
## Annotation types

Wireup supports two types of annotations. Using Python's `Annotated` or by using default values.

### Annotated

This is the preferred method for Python 3.9+ and moving forward. It is also recommended to
backport this using `typing_extensions` for Python 3.8.


```python
@container.autowire
def target(
    env: Annotated[str, Wire(param="env_name")],
    logs_cache_dir: Annotated[str, Wire(expr="${cache_dir}/logs")],
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

### Explicit injection annotation
 Even though annotating services is optional, you CAN still annotate them to be explicit about what will 
 be injected. This also has the benefit of making the container throw when such as service
 does not exist instead of silently skipping this parameter.

```python
@container.autowire
def target(random_service: Annotated[RandomService, Wire()]):
    ...
```
