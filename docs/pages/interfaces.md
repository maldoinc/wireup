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

## Injecting All Implementations

When you need every registered implementation of an interface, inject them as a `Set[T]`.

```python
from typing import Set
from wireup import Injected, inject_from_container, injectable


@injectable(as_type=Cache, qualifier="redis")
class RedisCache(Cache): ...


@injectable(as_type=Cache, qualifier="memory")
class InMemoryCache(Cache): ...


@inject_from_container(container)
def warm_all(caches: Injected[Set[Cache]]) -> None:
    for cache in caches:
        cache.warm()
```

Wireup resolves the set at injection time by iterating every impl of the inner type. Factory functions with
heterogeneous dependencies are supported: each impl's own deps are resolved through the normal container machinery
before the set is assembled.

!!! note "Resolution timing"

    The set reflects the registry state at the moment of resolution. Singleton consumers freeze the set at first
    resolution — once the consumer is cached, the set is cached with it — matching how any singleton's state is
    frozen after first construction. Transient and scoped consumers see impls added via `container.extend()` on
    their next resolution.

## Injecting Implementations by Qualifier

Use `Mapping[str, T]` to receive qualifier → implementation pairs. Each qualified impl becomes a keyed entry in
the injected dict.

```python
from typing import Mapping
from wireup import Injected, inject_from_container, injectable


@injectable(as_type=Cache, qualifier="redis")
class RedisCache(Cache): ...


@injectable(as_type=Cache, qualifier="memory")
class InMemoryCache(Cache): ...


@inject_from_container(container)
def pick_cache(caches: Injected[Mapping[str, Cache]], name: str) -> Cache:
    return caches[name]
```

Map resolution uses the same machinery as `Set[T]` — wireup iterates registered impls, resolves each via its
compiled factory, and keys the result by qualifier.

!!! note "Unqualified impls"

    Implementations registered without a qualifier have no key to index under, so they are not included in the
    map. Use `Set[T]` when you want every implementation regardless.

## `as_type` with Optional Types

When registering factory functions that return optional types (e.g. `Cache | None`), the binding is automatically
registered as optional.

```python
@injectable(as_type=Cache)
def make_cache() -> RedisCache | None: ...
```

This acts as if the factory was registered with `as_type=Cache | None`, allowing you to inject `Cache | None` or
`Optional[Cache]`.
