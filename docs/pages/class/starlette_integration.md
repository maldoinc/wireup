## wireup.integration.flask

::: wireup.integration.starlette

!!! note
    For best performance, use regular functions rather than callables or closures
    as dependencies. Callables and closures are not hashable and cannot be cached
    by the injection system.