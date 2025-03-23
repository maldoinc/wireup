The container can also hold configuration parameters to configure services.
This feature allows self-contained service declarations by adding `@service` and annotations to indicate what to inject.

!!! warning
    **Parameters are for application configuration only**. 
    They should not be used to pass values around or as a global session object.

    Use parameters for app configuration like environment name, database URL, mailer URL, etc.

### Inject by name

To inject a parameter by name, annotate the type with `Inject(param="param_name")`.

```python
@service
class GithubClient:
    def __init__(self, api_key: Annotated[str, Inject(param="gh_api_key")]) -> None:
        ...
```

### Parameter expressions

You can interpolate parameters using a special syntax to retrieve and concatenate multiple parameter values.

**Note:** The result is a string, so non-string parameters will be converted using `str()`.

```python
def target(logs_dir: Annotated[str, Inject(expr="${cache_dir}/${env}/logs")]) -> None:
    ...
```

## 🏭 Class-based configuration

Wireup's parameter configuration is optional. You can use typed classes for configuration, supported via factories.

Register your settings as a service and inject them into factories like regular dependencies.

See [Use Without Annotations](use_without_annotations.md) for more info.