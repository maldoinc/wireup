## Upgrade 0.16.0 to 1.0

All deprecated functionality is now removed. Please refer to the deprecation notices for an upgrade path.

### Removed support for default values

Using `foo: str = Inject(...)` is now no longer supported and the container will ignore the default value. Instead use annotated types. `foo: Annotated[str, Inject(...)]`.

### Removed ParameterEnum

`ParameterEnum` has been completely removed. Instead you can use type definitions to store parameters. `AppNameParameter = Annotated[str, Inject(name="app_name")]`

### Removed `Wire`, `wire`

Instead of `Wire` or `wire` use `Inject` which is a drop-in replacement.

### Removed `wireup.container` global

The `wireup.container` global has been removed. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

### Removed `warmup_container`

Removed old utility function. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

### Removed old integrations

`wireup.integrations.flask_integration` has been removed in favor of `wireup.integrations.flask`.
The same for `wireup.integrations.fastapi_integration` has been removed in favor of `wireup.integrations.fastapi`.

### Removed `initialize_container`

Removed old utility function. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

### Removed `register_all_in_module`

Removed old utility function. Register services by passing `service_modules` to `wireup.create_*_container`.