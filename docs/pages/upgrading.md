## Upgrade 1.x to 2.0.0

* Wireup container itself has no breaking changes. The major version bump is due to a breaking change in the FastAPI
integration.
* Added new `middleware_mode` parameter to the `wireup.integration.fastapi.setup` call. Default value is `False`,
Wireup 1.x default is the equivalent of `middleware_mode=True`. See FastAPI integration docs for when to enable this
setting.

## Upgrade 0.16.0 to 1.0

With the API now stable, deprecated features have been removed. Refer to the deprecation notices for upgrade guidance.

#### Removed `wireup.DependencyContainer`

The previous container was overly complex. It has been split into `wireup.SyncContainer` and `wireup.AsyncContainer`.

Use `wireup.AsyncContainer` if you need to create async dependencies, as it supports both sync and async resources.

Changes include:

* Removed `@container.register`
    * Use `@service` on services or factories and specify the container during creation with `wireup.create_sync_container` or `wireup.create_async_container`.
* Removed `@container.abstract`
    * Similar to above, use the `@abstract` decorator.
* Removed `@container.autowire`
    * This is removed. See the [Apply the container as a decorator](apply_container_as_decorator.md) docs for details.
* Removed `container.has_type`.
* `wireup.create_container` is now `wireup.create_sync_container` and `wireup.create_async_container`.

#### Removed get_all, put methods of `ParameterBag`.

`ParameterBag` does not support mutations. Pass all parameters when creating the container.

#### Removed support for default values

Using `foo: str = Inject(...)` is no longer supported. Use annotated types instead: `foo: Annotated[str, Inject(...)]`.

#### Removed ParameterEnum

`ParameterEnum` is removed. Use type definitions for parameters: `AppNameParameter = Annotated[str, Inject(name="app_name")]`.

#### Removed `Wire`, `wire`

Replace `Wire` or `wire` with `Inject`.

#### Removed `wireup.container` global

The global `wireup.container` is removed. Create a container instance with `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed `warmup_container`

This utility function is removed. Create a container instance with `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed old integrations

`wireup.integrations.flask_integration` is replaced by `wireup.integrations.flask`.
`wireup.integrations.fastapi_integration` is replaced by `wireup.integrations.fastapi`.

#### Removed `initialize_container`

This utility function is removed. Create a container instance with `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed `register_all_in_module`

This utility function is removed. Register services by passing `service_modules` to `wireup.create_*_container`.

#### Removed `load_module`

No direct replacement. Create a container instance with `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed `FactoryDuplicateServiceRegistrationError`

Use `DuplicateServiceRegistrationError`.

#### Removed `ServiceLifetime` enum in favor of literals

Replace `ServiceLifetime.SINGLETON` with `"singleton"` and `ServiceLifetime.TRANSIENT` with `"transient"`.

### Django Integration

The `perform_wramup` setting is removed.

### Flask Integration

The `import_flask_config` setting is removed. Expose Flask config directly to `create_sync_container`. See Flask integration docs for details.

### FastAPI Integration

The integration no longer automatically exposes `fastapi.Request` as a Wireup dependency. Pass `wireup.integration.fastapi` in your service modules when creating a container if needed.