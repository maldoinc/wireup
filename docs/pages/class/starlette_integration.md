## wireup.integration.flask

::: wireup.integration.starlette

!!! note
    For best performance with `WireupTask`, prefer regular top-level functions for background task callbacks.
    Wireup creates cached injection wrappers for top-level functions, but callable objects and nested
    functions/closures do not benefit from that caching.