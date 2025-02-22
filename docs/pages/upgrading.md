## Upgrade 0.16.0 to 1.0

All deprecated functionality is now removed. Please refer to the deprecation notices for an upgrade path.

### Removed support for default values

Using `foo: str = Inject(...)` is now no longer supported and the container will ignore the default value. Instead use annotated types. `foo: Annotated[str, Inject(...)]`.


### Removed ParameterEnum

`ParameterEnum` has been completely removed. Instead you can use type definitions to store parameters. `AppNameParameter = Annotated[str, Inject(name="app_name")]`


### Removed `Wire`, `wire`

Instead of `Wire` or `wire` use `Inject` which is a drop-in replacement.


## Removed `wireup.container` global

The `wireup.container` global has been removed. Create your own container instance instead via `wireup.create_sync_container` or `wireup.create_async_container`.