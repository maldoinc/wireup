# Dependency Annotations

Wireup uses type annotations to resolve dependencies. In most cases, the type alone is sufficient, but some cases require additional metadata through annotations.

## When Are Annotations Required?

Wireup differentiates between injecting into its own services (those decorated with `@service`) and injecting into external targets.

### Annotation Requirements in Wireup Services

| Type of Dependency                      | Annotations Required? | What is Required |
| --------------------------------------- | --------------------- | ---------------- |
| Services                                | No                    |                  |
| Interface with only one implementation  | No                    |                  |
| Default implementation of an interface  | No                    |                  |
| Interface with multiple implementations | Yes                   | Qualifier        |
| Parameters                              | Yes                   | Parameter name   |
| Parameter expressions                   | Yes                   | Expression       |
 

### Annotation Requirements in External Targets

Annotations are always required when injecting into an external target, even if they are not normally required in Wireup services. You must annotate parameters with `Annotated[T, Inject()]` or its alias `Injected[T]`.

!!! abstract "Why is this required"
    In its own services, Wireup assumes full ownership of the dependencies, making empty annotations via `Inject()` redundant. However, when injecting into targets it doesn't own, annotations inform the container to interact only with certain parameters. This ensures compatibility with other libraries or frameworks that might provide additional arguments to the function.

    A major benefit of this, is that the container can now raise an error if you request to inject something it doesn't recognize.

## Examples

For Python 3.9+ (or 3.8+ with `typing_extensions`):

```python
@wireup.inject_from_container(container)
def configure(
    # Inject configuration parameter
    env: Annotated[str, Inject(param="app_env")],
    
    # Inject dynamic expression
    log_path: Annotated[str, Inject(expr="${data_dir}/logs")],
    
    # Inject service
    service: Injected[MyService, Inject()],

    # Injected is an alias of Annotated[T, Inject()]
    service: Injected[MyService],
    
    # Inject specific implementation
    db: Annotated[Database, Inject(qualifier="readonly")]
):
    ...
```
