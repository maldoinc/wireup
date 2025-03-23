!!! warning
    When using the provided integrations, this is automatically handled for you.
    Only use this if you're injecting Wireup dependencies in a framework without an integration.

Instead of retrieving services via `container.get` or parameters via `container.params`, you can inject them by applying the container as a decorator.

The goal is to go from this:

```python
def awesome_function() -> None:
    random = container.get(RandomService)
    env_name = container.params.get("env")

    with container.enter_scope() as scoped_container:
        scoped_service = scoped_container.get(ScopedService)
```

To having the dependencies injected directly into the function.

## Implementation

Wireup provides a decorator called `wireup.inject_from_container`.
The container will enter a scope before executing the function, inject all dependencies and exit the scope once the function returns.

!!! warning
    When injecting on decorated functions, the container will only interact with parameters annotated with `Injected[T]` or `Annotated[T, Inject()]`
    (the two are equivalent, `Injected[T]` is only an alias).

```python
from wireup import Injected

@wireup.inject_from_container(container)
def awesome_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

If you have already created a scoped container elsewhere, you can supply a callable that returns it as the second argument. Wireup will use that and not enter a new scope.

```python
scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")

@wireup.inject_from_container(container, scoped_container.get)
def awesome_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

You can also alias the decorator for a cleaner look.

```python
scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")
injected = wireup.inject_from_container(container, scoped_container.get)

@injected
def awesome_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```


## Good to know

* This function works with both sync and async containers.
* To inject `async def` functions you need an async container created via `wireup.create_async_contaier`.

## Function documentation

### `wireup.inject_from_container`

::: wireup._decorators.inject_from_container

