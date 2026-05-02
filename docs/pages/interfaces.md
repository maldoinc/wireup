Use protocols or abstract base classes (ABCs) to define the behavior your application needs, separately from how it is
implemented. This allows you to easily switch between different implementations, for example using an in-memory
repository during testing instead of a real database.

For generic repository patterns and other parameterized types, see [Generic Dependencies](generic_dependencies.md).

## Basic Usage

You can use the `as_type` parameter in `@injectable` to register an injectable as any other type. This is commonly used
to bind a concrete class to a Protocol or an Abstract Base Class.

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
    Python type system limitation. If you want static guarantees, consider using factory functions with return type
    annotations instead of class decorators.

!!! note "Runtime Validation"

    Wireup performs runtime validation for `as_type` with the following behavior:

    - Non-protocol targets (`ABC`/regular classes): strict `issubclass` validation.
    - `@runtime_checkable` protocols: best-effort runtime validation.
    - Non-runtime-checkable protocols: no runtime structural validation.

    To get the most reliable guarantees:

    - Prefer factory return types over `as_type` when possible, since return annotations are statically checkable.
    - Prefer `ABC`s when you need strict runtime enforcement.
    - Mark protocols as `@runtime_checkable` if you want Wireup to attempt runtime checks.

    ______________________________________________________________________

    With factories, you control the registration type via the return annotation, which gives stronger static checks:

    ```python
    from wireup import injectable


    @injectable
    def make_cache() -> Cache:
        return InMemoryCache()
    ```

    This is equivalent to:

    ```python
    @injectable(as_type=Cache)
    class InMemoryCache: ...
    ```

    Use `as_type` when you want to register under a different type while keeping the original implementation type for other
    direct uses.

## Multiple Implementations

When you have multiple implementations of the same type, use **qualifiers** to distinguish between them. This is useful
for environment-specific behavior (e.g., in-memory cache in development, Redis in production) or feature flags.

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
    from enum import StrEnum


    class CacheType(StrEnum):
        MEMORY = "memory"
        REDIS = "redis"


    @injectable(as_type=Cache, qualifier=CacheType.REDIS)
    class RedisCache: ...
    ```

!!! tip "Use Type Aliases for Repeated Qualified Injections"

    If you repeatedly inject the same qualified dependency, consider creating a type alias once and reusing it:

    ```python
    from typing import Annotated
    from wireup import Inject, Injected, inject_from_container

    RedisCacheDep = Annotated[Cache, Inject(qualifier="redis")]


    @inject_from_container(container)
    def main(
        default_cache: Injected[Cache],
        redis_cache: RedisCacheDep,
    ): ...
    ```

## Default Implementation

You can register a default implementation by omitting the qualifier on one of the implementations. When `Cache` is
requested without a qualifier, the default will be injected.

```python
from typing import Annotated
from wireup import Inject, injectable, Injected, inject_from_container


@injectable(as_type=Cache)
class InMemoryCache: ...


@injectable(as_type=Cache, qualifier="redis")
class RedisCache: ...


@inject_from_container(container)
def main(
    # Default implementation: InMemoryCache
    memory_cache: Injected[Cache],
    # RedisCache: Qualified via qualifier="redis".
    redis_cache: Annotated[Cache, Inject(qualifier="redis")],
): ...
```

## Collection Injection

When a type has one or more registrations, you can request all of them at once as a collection. Collection injection
returns every registration for the requested type. If you used `as_type` to register under a different type, the collection includes the `as_type` target, not the original.

```python
from collections.abc import Hashable, Mapping
from typing import Protocol
from wireup import create_sync_container, injectable


class Cache(Protocol):
    def get(self, key: str) -> str: ...


@injectable(as_type=Cache)
class InMemoryCache:
    def get(self, key: str) -> str:
        return f"memory:{key}"


@injectable(as_type=Cache, qualifier="redis")
class RedisCache:
    def get(self, key: str) -> str:
        return f"redis:{key}"
```

### Supported Collection Types

Collection injection only supports `collections.abc.Sequence[T]` and `collections.abc.Mapping[Hashable, T]`.
Requesting `typing.Sequence[T]` or `typing.Mapping[K, V]` raises `UnknownServiceRequestedError` with a hint pointing
at the corresponding `collections.abc` type.

### `Sequence[T]`

Use `collections.abc.Sequence[T]` to receive every registration for `T` in registration order.

```python
from collections.abc import Sequence
from wireup import injectable


@injectable
class CacheReporter:
    def __init__(self, caches: Sequence[Cache]) -> None:
        self.caches = caches
```

`Sequence[T]` includes every registration for `T` in registration order, including the unqualified default, if
present, plus any qualified implementations.

### `Mapping[Hashable, T]`

Use `collections.abc.Mapping[Hashable, T]` to receive every registration for `T` keyed by qualifier.

```python
from dataclasses import dataclass

from wireup import injectable


@injectable
@dataclass
class CacheRouter:
    def __init__(self, caches: Mapping[Hashable, Cache]) -> None:
        self.caches = caches

    def default(self) -> Cache:
        return self.caches[None]
```

`Mapping[Hashable, T]` includes every registration for `T`, keyed by qualifier. The unqualified default is keyed
under `None`.

### Custom Collection Factories

Built-in collection injection covers `collections.abc.Sequence[T]` and `collections.abc.Mapping[Hashable, T]`.
When you need a filtered, transformed, or domain-specific collection shape, create it with a regular factory.

This is an advanced pattern. Most applications can inject `Sequence[T]` or `Mapping[Hashable, T]` directly.

Use a custom collection factory when you want to:

- filter out some implementations
- reshape the built-in mapping into application-specific keys
- expose a collection under a domain-specific type

#### Filter a Collection

You can build a derived collection by injecting the built-in `Mapping[Hashable, T]` and returning a new type.

```python
from collections.abc import Hashable, Mapping
from typing import NewType, Protocol

from wireup import injectable


class Cache(Protocol):
    def source(self) -> str: ...


# Optionally NewType-annotate the result for better type safety and readability.
FilteredCaches = NewType("FilteredCaches", list[Cache])


@injectable(as_type=Cache)
class MemoryCache:
    def source(self) -> str:
        return "memory"


@injectable(as_type=Cache, qualifier="redis")
class RedisCache:
    def source(self) -> str:
        return "redis"


@injectable
def filtered_caches(
    caches: Mapping[Hashable, Cache],
) -> FilteredCaches:
    return FilteredCaches(
        [cache for key, cache in caches.items() if key is not None]
    )
```

`filtered_caches` receives the built-in qualifier mapping for `Cache`, removes the default entry under `None`, and
registers the result as `FilteredCaches`.

Consumers can then request the derived collection directly:

```python
from wireup import injectable


@injectable
class CacheReporter:
    def __init__(self, caches: FilteredCaches) -> None:
        self.caches = caches
```

#### Reshape a Mapping

You can also build your own mapping type on top of `Mapping[Hashable, T]`.

```python
from collections.abc import Hashable, Mapping
from typing import NewType

from wireup import injectable

CacheMap = NewType("CacheMap", dict[str, Cache])


@injectable
def cache_map(caches: Mapping[Hashable, Cache]) -> CacheMap:
    return CacheMap(
        {
            "default": caches[None],
            **{
                str(key): value
                for key, value in caches.items()
                if key is not None
            },
        }
    )
```

This lets you keep Wireup's built-in qualifier-based collection injection while exposing the result under the shape
your application actually wants.

Start with the built-in collection types when they already match your needs:

- use `Sequence[T]` when order matters and qualifiers do not
- use `Mapping[Hashable, T]` when you want qualifier-based access

Reach for a custom factory only when you need additional filtering, transformation, or a distinct domain type.

## `as_type` with Optional Types

When registering factory functions that return optional types (e.g. `Cache | None`), the binding is automatically
registered as optional.

```python
@injectable(as_type=Cache)
def make_cache() -> RedisCache | None: ...
```

This acts as if the factory was registered with `as_type=Cache | None`, allowing you to inject `Cache | None` or
`Optional[Cache]`.
