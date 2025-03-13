# Dependency Annotations

Wireup uses type annotations to resolve dependencies. Some cases require additional metadata through annotations.

## When Are Annotations Required?

| Type of Dependency                      | Annotations required? | What is required |
| --------------------------------------- | --------------------- | ---------------- |
| Services                                | No                    |                  |
| Interface with only one implementation  | No                    |                  |
| Default implementation of an interface  | No                    |                  |
| Interface with multiple implementations | Yes                   | Qualifier        |
| Parameters                              | Yes                   | Parameter name   |
| Parameter expressions                   | Yes                   | Expression       |
 

## Example

For Python 3.9+ (or 3.8+ with `typing_extensions`):

```python
@container.autowire
def configure(
    # Inject configuration parameter
    env: Annotated[str, Inject(param="APP_ENV")],
    
    # Inject dynamic expression
    log_path: Annotated[str, Inject(expr="${data_dir}/logs")],
    
    # Explicitly inject service
    service: Annotated[MyService, Inject()],
    
    # Inject specific implementation
    db: Annotated[Database, Inject(qualifier="replica")]
):
    ...
```

!!! tip
    While service annotations are optional, using them helps catch missing dependencies early.
