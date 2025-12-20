# Factories and Resource Management

Use factories to handle complex service creation logic or resource management that can't be done with simple class constructors.

## Use cases

* Object construction needs additional logic or configuration.
* Create optional dependencies.
* Depending on the runtime environment or configuration, you may need to create different objects 
inheriting from the same base class/protocol.
* Inject a model/dto which represents the result of an action, such as the current authenticated user.
* Inject a class from another library where it's not possible to add annotations.
* Inject strings, ints and other built-in types.

In order for the container to inject these dependencies, you must decorate the factory with `@service` and register
it with the container. Return type annotation of the factory is required as it denotes what will be built.


## Generator Factories

Use generator factories when a service requires cleanup (like database connections or network resources).

=== "Generators"

    ```python
    @service
    def db_session_factory() -> Iterator[Session]:
        db = Session()
        try:
            yield db
        finally:
            db.close()
    ```

=== "Context Manager"

    ```python
    @service
    def db_session_factory() -> Iterator[Session]:
        with contextlib.closing(Session()) as db:
            yield db
    ```

=== "Async Context Manager"

    ```python
    @service
    async def client_session_factory() -> ClientSession:
        async with ClientSession() as sess:
            yield sess
    ```

!!! note "Generator Factories"
    Generator factories must yield exactly once. Yielding multiple times will result in cleanup not being performed.


## Implement strategy pattern

Assume a base class `Notifier` with implementations that define how the notification is sent (IMAP, POP, WebHooks, etc.)
Given a user it is possible to instantiate the correct type of notifier based on user preferences.

```python
from wireup import service

@service(lifetime="scoped")
def get_user_notifier(
    user: AuthenticatedUser, 
    slack_notifier: SlackNotifier, 
    email_mailer: EmailNotifier
) -> Notifier:
    notifier = ...  # get notifier type from preferences.

    return notifier
```

When injecting `Notifier` the correct type will be injected based on the authenticated user's preferences.

## Inject a third-party class

You can use factories to inject a class which you have not declared yourself and as such, cannot annotate. 
Let's take redis client as an example. 

```python
from wireup import service

@service
def redis_factory(redis_url: Annotated[str, Inject(param="redis_url")]) -> Redis:
    return redis.from_url(redis_url)
```


## Inject Models

Assume the authenticated user is provided by `AuthService`. You may choose to allow the user to be injected directly
instead of having to call `auth_service.get_current_user()` everywhere.


```python
from wireup import service

@service(lifetime="scoped")
def get_current_user(auth_service: AuthService) -> AuthenticatedUser:
    return auth_service.get_current_user()
```

## Inject built-in types

If you want to inject resources which are just strings, ints, or other built-in types then you can use a factory in
combination with `NewType`.
Note that since Wireup uses types to identify dependencies, new types are strongly recommended for this use case.

```python title="factories.py"
AuthenticatedUsername = NewType("AuthenticatedUsername", str)

@service
def authenticated_username_factory(auth: SomeAuthService) -> AuthenticatedUsername:
    return AuthenticatedUsername(...)
```

This can now be injected as usual by annotating the dependency with the new type.

---


## Error Handling

When using generator factories with scoped or transient lifetimes, unhandled errors that occur within the 
scope are  automatically propagated to the factories. This enables proper error handling, such as rolling back 
database transactions or cleaning up resources when operations fail.

```python
@service(lifetime="scoped")
def db_session_factory(engine: Engine) -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
    except Exception as e:
        # Error occurred somewhere in the scope - rollback the transaction
        session.rollback()
        raise
    else:
        # No errors - commit the transaction
        session.commit()
    finally:
        # Always close the session
        session.close()
```

!!! note "Suppressing Errors"
    Factories may perform cleanup (for example, rolling back a transaction), but they cannot suppress the original error, that exception will still be propagated. Wireup enforces this so cleanup code cannot
    change the program's control flow by swallowing errors.

    If a factory raises additional exceptions during teardown, Wireup will temporarily catch those exceptions
    so it can finish cleaning up all generator factories. After cleanup completes, the teardown exceptions are
    re-raised alongside the primary exception.


### Database Transaction Example

```python
from typing import Iterator
from sqlalchemy.orm import Session
from wireup import service, Injected

@service(lifetime="scoped")
class UserService:
    # Uses Session as defined above.
    def __init__(self, db: Session) -> None:
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        # Database operations here
        ...

# Usage in a web framework (FastAPI example)
@app.post("/users")
def create_user(
    user_data: UserCreate, 
    user_service: Injected[UserService]
) -> User:
    # If this raises an exception, the database transaction
    # will automatically be rolled back
    return user_service.create_user(user_data)
```

!!! tip "Framework Integration"
    When using Wireup with web frameworks, each request automatically gets its own scope. 
    When using this feature, database transactions and other resources are automatically managed per request,
    with automatic rollback on any unhandled exception.

---

## Optional Dependencies and Factories

You can both request Optional dependencies and create factories that return optional values. This is useful when a service might not be available or when you want to make a dependency optional.


!!! important "Service Registration Required"
    When using optional dependencies, the service providing the optional dependency **must still be registered** in the container. The service cannot be absent - it can only return `None`. This means you must register a factory that can potentially return `None`,
    rather than simply not registering the service at all.

### Factories Returning Optional Values

Sometimes you want a factory to return `None` when certain conditions aren't met. A common example is a service that requires configuration to be available:

```python
@service
def cache_factory(
    redis_url: Annotated[str | None, Inject(param="redis_url")],
) -> Redis | None:
    return Redis.from_url(redis_url) if redis_url else None
```

### Requesting Optional Dependencies

When a service has an optional dependency, simply use `T | None` or `Optional[T]`.

=== "Python 3.10+"

    ```python hl_lines="1 3"
    @service
    class UserService:
        def __init__(self, cache: Cache | None) -> None:
            self.cache = cache

        def get_user(self, id: str) -> User:
            if self.cache:
                cached = self.cache.get(id)
                if cached:
                    return cached
            # Fallback to database
            ...
    ```

=== "Python <3.10"

    ```python hl_lines="1 3"
    @service
    class UserService:
        def __init__(self, cache: Optional[Cache]) -> None:
            self.cache = cache

        def get_user(self, id: str) -> User:
            if self.cache:
                cached = self.cache.get(id)
                if cached:
                    return cached
            # Fallback to database
            ...
    ```

!!! tip "Null Object Pattern"
    For cleaner code when dealing with optional dependencies, consider using the [Null Object Pattern](tips_tricks.md#)
    instead of conditional checks throughout your code.


**Injection vs. Direct Access**: Optional dependencies can be injected into services and decorated functions, but there's an important distinction when accessing them directly:

```python
# ✅ This works - injecting optional dependencies
@service
class UserService:
    def __init__(self, cache: Optional[Cache]) -> None: ...

# ✅ This works - getting the service directly
cache = container.get(Cache)  # Returns None if factory returns None

# ❌ This doesn't work - cannot get Optional types directly
cache = container.get(Optional[Cache]) 
```
