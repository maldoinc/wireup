## Upgrade 0.16.0 to 1.0

As the api is now stable, deprecated functionality has been removed. Please refer to the deprecation notices for an upgrade path.

### Removed `wireup.DependencyContainer`

The current container was doing too much and was a result of initial attempts to provide a simple api. It has now been split in two: `wireup.SyncContainer` and `wireup.AsyncContainer`.

If you need to create async dependencies anywhere in your application then you should use the async version of the container.
As it will be able to create both sync and async resources.

As a result of this, the following has changed:

* `@container.register`
    * If you were manually registering services with the container, that has now been removed. You should instead use `@service` on services or factories and point the container to then at creation time when calling `wireup.create_sync_container` or `wireup.create_async_container`.
* `@container.abstract`
    * Same as above except use `@abstract` decorator.
* `@container.autowire`
    * This has also been removed. Refer to the relevant docs for an upgrade path: [Apply the container as a decorator](apply_container_as_decorator.md).
* `wireup.create_container` is now `wireup.create_sync_container` and `wireup.create_async_container`.

#### Removed support for default values

Using `foo: str = Inject(...)` is now no longer supported and the container will ignore the default value. Instead use annotated types. `foo: Annotated[str, Inject(...)]`.

#### Removed ParameterEnum

`ParameterEnum` has been completely removed. Instead you can use type definitions to store parameters. `AppNameParameter = Annotated[str, Inject(name="app_name")]`.

#### Removed `Wire`, `wire`

Instead of `Wire` or `wire` use `Inject` which is a drop-in replacement.

#### Removed `wireup.container` global

The `wireup.container` global has been removed. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed `warmup_container`

Removed old utility function. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed old integrations

`wireup.integrations.flask_integration` has been removed in favor of `wireup.integrations.flask`.
The same for `wireup.integrations.fastapi_integration` has been removed in favor of `wireup.integrations.fastapi`.

#### Removed `initialize_container`

Removed old utility function. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed `register_all_in_module`

Removed old utility function. Register services by passing `service_modules` to `wireup.create_*_container`.


#### Removed `load_module`

No direct replacement is offered. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.

#### Removed `FactoryDuplicateServiceRegistrationError`

Use `DuplicateServiceRegistrationError` instead.