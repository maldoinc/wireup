Use `@wrap_with_dependencies` to handle cross-cutting concerns such as timing, audit logging, authorization, and rate limiting with reusable decorators that declare their own injected dependencies.

Think of it as a Wireup-aware `functools.wraps`: your decorator's extra dependencies resolve from the same scope as the decorated function's. Reuse it across routes, commands, and jobs without capturing a container or importing a framework's injection helpers.

!!! info "Requires an injection site"

    This helper does not inject dependencies or create a scope. Use your decorator where Wireup is already expected to perform injection.

## Basic Usage

Apply `@wrap_with_dependencies(fn)` where you would normally use `@functools.wraps(fn)`. Declare the wrapper's dependencies as keyword-only parameters between `*args` and `**kwargs`:

Here, `AuditRepository` is an existing injectable repository with an `add` method.

```python
import wireup
from wireup import Injected, injectable, wrap_with_dependencies

from myapp.repositories import AuditRepository


@injectable(lifetime="scoped")
class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def record(self, operation: str) -> None:
        self.repository.add(operation)


def audited(fn):
    @wrap_with_dependencies(fn)
    def wrapped(*args, audit: Injected[AuditService], **kwargs):
        audit.record(fn.__qualname__)
        return fn(*args, **kwargs)

    return wrapped


container = wireup.create_sync_container(
    injectables=[AuditRepository, AuditService]
)


@wireup.inject_from_container(container)
@audited
def greet(name: str) -> str:
    return f"Hello, {name}!"


assert greet("world") == "Hello, world!"
```

Place `@inject_from_container` above your decorator. With automatic framework injection, place your decorator below route or command registration so the framework sees the combined signature.

!!! tip "Decorator behavior"

    Write the wrapper as you would any Python decorator: await coroutine targets, use `yield from` for generators,
    and `async for` with `yield` for async generators. `wrap_with_dependencies` exposes the wrapper's dependencies
    to Wireup so they resolve from the same scope as the target's. Your wrapper remains responsible for calling, awaiting, or iterating over the target.

## Requirements and Scope

This is a regular Python decorator, with the following additional rules for Wireup injection:

- Accept `*args` and `**kwargs`, with additional wrapper parameters declared keyword-only.
- Use `Injected[T]` or `Annotated[T, Inject(...)]` for injection. Unmarked parameters remain caller-supplied or use defaults.
- Keep additional parameter names unique across the target and stacked decorators; duplicates raise `WireupError`.
- Keep types referenced by stringified annotations available at runtime, outside `TYPE_CHECKING` blocks.

Wrapper and target dependencies resolve from the same scope. Parameters requesting the same scoped service receive the
same instance. All dependencies are resolved before any wrapper body runs, so wrappers cannot intercept construction
or its errors.

## API Reference

::: wireup.wrap_with_dependencies
