# Dependency Annotations

Wireup uses type annotations to figure out which dependencies to inject. Most of the time, just the type is enough, but sometimes you need to add extra information using injection annotations.

## When Do You Need Annotations?

Whether you need annotations depends on where you're injecting into Wireup services or into external targets.

### Injecting into Wireup Services

For classes and functions marked with `@service`:

| Dependency Type                         | Annotations Needed? | Required Information |
| --------------------------------------- | ------------------- | -------------------- |
| Services                                | No                  | -                    |
| Interface with single implementation    | No                  | -                    |
| Default implementation of interface     | No                  | -                    |
| Interface with multiple implementations | Yes                 | Qualifier            |
| Parameters                              | Yes                 | Parameter name       |
| Parameter expressions                   | Yes                 | Expression template  |

### Injecting into External Code

When you're injecting into code that Wireup doesn't manage (like framework route handlers), you always need annotations. Use either `Annotated[T, Inject(...)]` or the shorthand `Injected[T]`.

!!! info "Why external code needs annotations"
    Inside Wireup services, Wireup assumes full ownership of all dependencies, so basic `Injected[T]` annotations are redundant. For external targets, annotations explicitly tell Wireup to handle those parameters.

## Usage Examples

Here's how to use annotations in Python 3.9+ (or Python 3.8+ with `typing_extensions`):

```python
@wireup.inject_from_container(container)
def configure(
    # Inject a configuration parameter by name
    env: Annotated[str, Inject(param="app_env")],
    
    # Inject a computed value using parameter substitution
    log_path: Annotated[str, Inject(expr="${data_dir}/logs")],
    
    # Inject a service (explicit annotation required for external targets)
    service: Annotated[MyService, Inject()],

    # Alternative shorthand syntax for service injection
    service: Injected[MyService],
    
    # Inject a specific implementation when multiple exist
    db: Annotated[Database, Inject(qualifier="readonly")]
):
    ...
```
