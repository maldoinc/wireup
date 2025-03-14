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

Wireup provides a decorator called `autowire`. The container will enter a scope before executing the function and exit the scope once the function returns.

```python
@autowire(container)
def awesome_function(
    service: RandomService, 
    scoped_service: ScopedService, 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

If you have already created a scoped container elsewhere, you can supply a callable that returns it as the second argument. Wireup will use that and not enter a new scope.

```python
scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")

@autowire(container, scoped_container.get)
def awesome_function(
    service: RandomService, 
    scoped_service: ScopedService, 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

You can also alias the decorator for a cleaner look.

```python
scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")
autowired = autowire(container, scoped_container.get)

@autowired
def awesome_function(
    service: RandomService, 
    scoped_service: ScopedService, 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

!!! note
    This function works with both sync and async containers.

## Function documentation

### `autowire`

::: wireup._decorators.autowire

