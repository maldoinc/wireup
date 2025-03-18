In addition to service objects, the container also holds configuration, called parameters
that can be used to configure services.

This is an optional feature that enables self-contained service declarations where you just add `@service`
and any annotations to let Wireup know what to inject. 

!!! warning
    **Parameters represent application configuration**. 
    They are not intended to pass values around or to be used as a global session object.

    Store only app configuration such as environment name, database url, mailer url etc.

### Injection

#### By name

To inject a parameter by name, annotate the type with `Inject(param="param_name")`.

```python
@service
class GithubClient:
    def __init__(self, api_key: Annotated[str, Inject(param="gh_api_key")]) -> None:
        ...
```

#### Parameter expressions

It is possible to interpolate parameters using a special syntax. This will enable you to retrieve several parameters at once and concatenate their values together.

**Note:** As the result is a string, non-string parameters will be converted using `str()`.

```python
def target(logs_dir: Annotated[str, Inject(expr="${cache_dir}/${env}/logs")]) -> None:
    ...
```

## 🏭 Class-based configuration

While Wireup provides its own configuration mechanism in the form of parameters, it is entirely optional.
If you prefer using typed classes for configuration, they are also supported via factories.

The main idea is to register your settings as a service and inject it into factories like a regular dependency.

See [Use Without Annotations](use_without_annotations.md) for more info.