Use generator factories when an injectable requires cleanup, such as database connections, file handles, or network
resources.

## Generator Factories

Generator factories use Python's `yield` statement to manage resource lifecycle:

1. **Setup**: Code before `yield` runs when the dependency is created.
1. **Use**: The yielded value is injected into consumers.
1. **Teardown**: Code after `yield` runs when the scope closes.

=== "Generators"
    ```python
    @injectable
    def db_session_factory() -> Iterator[Session]:
        db = Session()
        try:
            yield db
        finally:
            db.close()
    ```

=== "Context Manager"
    ```python
    @injectable
    def db_session_factory() -> Iterator[Session]:
        with contextlib.closing(Session()) as db:
            yield db
    ```

=== "Async Context Manager"
    ```python
    from typing import AsyncIterator


    @injectable
    async def client_session_factory() -> AsyncIterator[ClientSession]:
        async with ClientSession() as sess:
            yield sess
    ```

!!! note "Generator Factories"
    Generator factories must yield exactly once. Yielding multiple times will result in cleanup not being performed.

## Error Handling

When using generator factories with scoped or transient lifetimes, unhandled errors that occur within the scope are
automatically propagated to the factories. This enables conditional cleanup, such as rolling back uncommitted database
changes when operations fail.

```python
@injectable(lifetime="scoped")
def db_session_factory(engine: Engine) -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
    except Exception:
        # Error occurred - rollback any uncommitted changes
        session.rollback()
        raise
    finally:
        # Always close the session
        session.close()
```

!!! note "Suppressing Errors"
    Factories cannot suppress exceptions, they can perform cleanup, but the original error will always propagate. This
    ensures cleanup code doesn't accidentally change your program's control flow.
