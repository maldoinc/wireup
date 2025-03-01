Autowiring relies on annotations or hints to be able to inject dependencies.
When it is not possible to automatically locate a given dependency, it must be annotated with additional metadata.

## When do you need to provide annotations.

| Injecting                               | Annotations required? | What is required     |
|-----------------------------------------|-----------------------|----------------------|
| Services                                | No                    |                      |
| Interface with only one implementation  | No                    |                      |
| Default implementation of an interface  | No                    |                      |
| Interface with multiple implementations | Yes                   | Qualifier            |
| Parameters                              | Yes                   | Parameter name       |
| Parameter expressions                   | Yes                   | Expression           |
 
## Annotation types

Wireup supports two types of annotations. Using Python's `Annotated` and default values.

### Annotated

This is the preferred method for Python 3.9+ and moving forward. It is also recommended to
backport this using `typing_extensions` for Python 3.8.


```python
@container.autowire
def target(
    env: Annotated[str, Inject(param="env_name")],
    logs_cache_dir: Annotated[str, Inject(expr="${cache_dir}/logs")],
):
    ...
```

### Explicit injection annotation
Even though annotating services is optional, you CAN still annotate them to be explicit about what will 
be injected. This also has the benefit of raising when the service does not exist instead
of silently skipping this parameter.

```python
@container.autowire
def target(random_service: Annotated[RandomService, Inject()]):
    ...
```
