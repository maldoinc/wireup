Use protocols or abstract base classes (ABCs) to define the behavior your application needs, separately from how it is
implemented. This allows you to easily switch between different implementations, for example using an in-memory
repository during testing instead of a real database.

## Basic Usage

You can use the `as_type` parameter in `@injectable` to register a service as any other type. This is commonly used to
bind a concrete class to a Protocol or an Abstract Base Class.

=== "Protocol"

    ```python hl_lines="10"
    from typing import Protocol
    from wireup import injectable


    class Cache(Protocol):
        def get(self, key: str) -> str | None: ...
        def set(self, key: str, value: str): ...


    @injectable(as_type=Cache)
    class InMemoryCache: ...
    ```

=== "Abstract Base Class"

    ```python hl_lines="13"
    from abc import ABC, abstractmethod
    from wireup import injectable


    class Cache(ABC):
        @abstractmethod
        def get(self, key: str) -> str | None: ...

        @abstractmethod
        def set(self, key: str, value: str): ...


    @injectable(as_type=Cache)
    class InMemoryCache(Cache):
        def get(self, key: str) -> str | None: ...
        def set(self, key: str, value: str): ...
    ```

!!! warning "Type Checking Limitation"

    Type checkers cannot verify that the decorated class implements the protocol or ABC specified in `as_type`. This is a
    Python type system limitation. Ensure your implementation is correct or use explicit inheritance.

## Multiple Implementations

When you have multiple implementations of the same type, use **qualifiers** to distinguish between them.

```python
from typing import Annotated
from wireup import Inject, injectable, inject_from_container


@injectable(as_type=Cache, qualifier="memory")
class InMemoryCache: ...


@injectable(as_type=Cache, qualifier="redis")
class RedisCache: ...


@inject_from_container(container)
def main(
    memory_cache: Annotated[Cache, Inject(qualifier="memory")],
    redis_cache: Annotated[Cache, Inject(qualifier="redis")],
): ...
```

!!! tip "Qualifiers don't have to be strings"

    You can avoid magic strings by using Enums or hashable types for qualifiers. This prevents typos and makes refactoring
    easier.

    ```python
    class CacheType(StrEnum):
        MEMORY = "memory"
        REDIS = "redis"


    @injectable(as_type=Cache, qualifier=CacheType.REDIS)
    class RedisCache: ...
    ```

## Default Implementation

You can register a default implementation by omitting the qualifier on one of the services. When `Cache` is requested
without a qualifier, the default will be injected.

```python
@injectable(as_type=Cache)
class InMemoryCache: ...


@injectable(as_type=Cache, qualifier="redis")
class RedisCache: ...


@wireup.inject_from_container(container)
def main(
    # Default implementation: InMemoryCache
    memory_cache: Injected[Cache],
    # RedisCache: Qualified via qualifier="redis".
    redis_cache: Annotated[Cache, Inject(qualifier="redis")],
): ...
```

## Optional Binding

When registering factory functions that return optional types (e.g. `Cache | None`), the binding is automatically
registered as optional.

```python
@injectable(as_type=Cache)
def make_cache() -> RedisCache | None: ...
```

This acts as if the factory was registered with `as_type=Cache | None`, allowing you to inject `Cache | None` or
`Optional[Cache]`.
