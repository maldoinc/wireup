Use factories to handle complex creation logic or resource management that can't be done with simple class constructors.

## Use cases

- Object construction needs additional logic or configuration.
- Create optional dependencies.
- Depending on the runtime environment or configuration, you may need to create different objects inheriting from the
    same base class/protocol.
- Inject a model/dto which represents the result of an action, such as the current authenticated user.
- Inject a class from another library where it's not possible to add annotations.
- Inject strings, ints and other built-in types.

In order for the container to inject these dependencies, you must decorate the factory with `@injectable` and register
it with the container. Return type annotation of the factory is required as it denotes what will be built.

!!! note "Generator Factories"

    If you need to perform cleanup (like database connections or network resources), use
    [generator factories](resources.md).

## Strategy pattern

Assume a base class `Notifier` with implementations that define how the notification is sent (IMAP, POP, WebHooks, etc.)
Given a user it is possible to instantiate the correct type of notifier based on user preferences.

```python
from wireup import injectable


@injectable(lifetime="scoped")
def get_user_notifier(
    user: AuthenticatedUser,
    slack_notifier: SlackNotifier,
    email_mailer: EmailNotifier,
) -> Notifier:
    notifier = ...  # get notifier type from preferences.

    return notifier
```

When injecting `Notifier` the correct type will be injected based on the authenticated user's preferences.

## Third-party classes

You can use factories to create classes which you have not declared yourself and as such, cannot annotate. Let's take
redis client as an example.

```python
from wireup import injectable


@injectable
def redis_factory(
    redis_url: Annotated[str, Inject(config="redis_url")],
) -> Redis:
    return redis.from_url(redis_url)
```

## Models and DTOs

Assume the authenticated user is provided by `AuthService`. You may choose to allow the user to be injected directly
instead of having to call `auth_service.get_current_user()` everywhere.

```python
from wireup import injectable


@injectable(lifetime="scoped")
def get_current_user(auth_service: AuthService) -> AuthenticatedUser:
    return auth_service.get_current_user()
```

## Injecting Primitives

If you want to inject resources which are just strings, ints, or other built-in types then you can use a factory in
combination with `NewType`. Note that since Wireup uses types to identify dependencies, new types are strongly
recommended for this use case.

```python title="factories.py"
AuthenticatedUsername = NewType("AuthenticatedUsername", str)


@injectable
def authenticated_username_factory(auth: AuthService) -> AuthenticatedUsername:
    return AuthenticatedUsername(...)
```

This can now be injected as usual by annotating the dependency with the new type.

______________________________________________________________________

## Optional Dependencies and Factories

You can both request Optional dependencies and create factories that return optional values. This is useful when an
injectable might not be available or when you want to make a dependency optional.

!!! important "Injectable Registration Required"

    When using optional dependencies, the injectable providing the optional dependency **must still be registered** in the
    container. The injectable cannot be absent - it can only return `None`. This means you must register a factory that can
    potentially return `None`, rather than simply not registering the injectable at all.

### Factories Returning Optional Values

Sometimes you want a factory to return `None` when certain conditions aren't met. A common example is an injectable that
requires configuration to be available:

```python
@injectable
def cache_factory(
    redis_url: Annotated[str | None, Inject(config="redis_url")],
) -> Redis | None:
    return Redis.from_url(redis_url) if redis_url else None
```

### Requesting Optional Dependencies

When an injectable has an optional dependency, simply use `T | None` or `Optional[T]`.

=== "Python 3.10+"

    ```python hl_lines="1 3"
    @injectable
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
    @injectable
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

**Direct Access**

When accessing optional dependencies directly from the container, you can retrieve them using `container.get()` just
like any other injectable. If the factory was registered with an optional return type you'll need to provide the union
type when retrieving it.

```python
cache = container.get(Optional[Cache])
cache = container.get(Cache | None)
```

!!! warning "Type Checking Limitation"

    Type checkers cannot fully verify `container.get(T | None)` or `container.get(Optional[T])` due to Python type system
    limitations. The call works correctly at runtime. Prefer using injection where possible.

!!! tip "Null Object Pattern for Optional Dependencies"

    Instead of adding conditional checks throughout your code, use the pattern to handle optional dependencies cleanly. It
    involves creating a noop implementation that can be used when the real implementation is not available.

    ```python title="services/cache.py"
    from wireup import injectable
    from typing import Any


    class Cache(Protocol):
        def get(self, key: str) -> Any | None: ...
        def set(self, key: str, value: str) -> None: ...


    class RedisCache: ...  # Real Redis implementation


    class NullCache:
        def get(self, key: str) -> Any | None:
            return None  # Always cache miss

        def set(self, key: str, value: str) -> None:
            return None  # Do nothing


    @injectable
    def cache_factory(
        redis_url: Annotated[str | None, Inject(config="redis_url")],
    ) -> Cache:
        return RedisCache(redis_url) if redis_url else NullCache()
    ```

    **Usage**

    === "Before: Optional Dependencies"

        ```python
        @injectable
        class UserService:
            def __init__(self, cache: Cache | None):
                self.cache = cache

            def get_user(self, user_id: str) -> User:
                # Guard required
                if self.cache and (cached := self.cache.get(f"user:{user_id}")):
                    return User.from_json(cached)

                user = self.db.get_user(user_id)

                # Guard required
                if self.cache:
                    self.cache.set(f"user:{user_id}", user.to_json())

                return user
        ```

    === "After: Null Pattern"

        ```python
        @injectable
        class UserService:
            def __init__(self, cache: Cache):
                self.cache = cache  # Always a Cache instance

            def get_user(self, user_id: str) -> User:
                if cached := self.cache.get(f"user:{user_id}"):
                    return User.from_json(cached)

                user = self.db.get_user(user_id)
                self.cache.set(f"user:{user_id}", user.to_json())
                return user
        ```
