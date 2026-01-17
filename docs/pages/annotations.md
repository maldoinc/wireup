Wireup uses type annotations to figure out which dependencies to inject. Most of the time, just the type is enough, but sometimes you need to add extra information using injection annotations.

## When Do You Need Annotations?

Whether you need annotations depends on where you're injecting into Wireup injectables or into external targets.

### Injecting into Wireup Injectables

For classes and functions marked with `@injectable`:

| Dependency Type                         | Annotations Needed? | Required Information |
| --------------------------------------- | ------------------- | -------------------- |
| Injectables                             | No                  | -                    |
| Interface with single implementation    | No                  | -                    |
| Default implementation of interface     | No                  | -                    |
| Interface with multiple implementations | Yes                 | Qualifier            |
| Configuration                           | Yes                 | Config key           |
| Configuration expression                | Yes                 | Expression template  |

### Injecting into External Code

When you're injecting into code that Wireup doesn't manage (like framework route handlers), you always need annotations. Use either `Annotated[T, Inject(...)]` or the shorthand `Injected[T]`.

!!! info "Why external code needs annotations"
    Inside Wireup injectables, Wireup assumes full ownership of all dependencies, so basic `Injected[T]` annotations are redundant. For external targets, annotations explicitly tell Wireup to handle those parameters without interfering with parameters provided by the framework or runtime.

## Usage Examples

Here's how to use annotations in Python 3.9+ (or Python 3.8+ with `typing_extensions`):

```python
@wireup.inject_from_container(container)
def configure(
    # Inject configuration by referencing its key
    env: Annotated[str, Inject(config="app_env")],
    
    # Inject a computed value using expressions
    log_path: Annotated[str, Inject(expr="${data_dir}/logs")],
    
    # Inject an injectable (explicit annotation required for external targets)
    service: Annotated[MyService, Inject()],

    # Alternative shorthand syntax for injectable injection
    my_service: Injected[MyService],
    
    # Inject a specific implementation when multiple exist
    db: Annotated[Database, Inject(qualifier="readonly")]
):
    ...
```
