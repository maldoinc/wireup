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

When injecting into an external target, annotations are always required, even if not typically needed in Wireup services. Annotate parameters with `Annotated[T, Inject()]` or its alias `Injected[T]`.

!!! abstract "Why is this required"
    In its own services, Wireup assumes full ownership of dependencies, making empty annotations via `Inject()` redundant. For external targets, annotations inform the container to interact only with specific parameters, ensuring compatibility with other libraries or frameworks.

    Explicit annotations allow the container to fail fast on unrecognized injection requests, improving reliability by catching errors early. They also enhance maintainability and readability by clearly documenting expected dependencies.

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
    service: Annotated[MyService, Inject()],

    # Injected is an alias of Annotated[T, Inject()]
    service: Injected[MyService],
    
    # Inject specific implementation
    db: Annotated[Database, Inject(qualifier="readonly")]
):
    ...
```
