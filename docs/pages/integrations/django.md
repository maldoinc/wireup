Dependency injection for Django is available via the first-party integration wireup provides, available in
`wireup.integration.django`.

## Installation

To install the integration, add `wireup.integration.django` to `INSTALLED_APPS` and define a new `WIREUP` setting.

```python title="settings.py"
from wireup.integration.django import WireupSettings


INSTALLED_APPS = [
    ...,
    "wireup.integration.django"
]

WIREUP = WireupSettings(
    # This is a list of top-level modules containing service registrations.
    # It can be either a list of strings or module types.
    service_modules=["mysite.polls.services"]
)
```


## Usage

### Define some services

```python title="mysite/polls/services/s3_manager.py"
from wireup import service


@service
class S3Manager:
    # Reference configuration by name.
    # This is the same name this appears in settings.
    def __init__(self, token: Annotated[str, Wire(parameter="S3_BUCKET_ACCESS_TOKEN")]):
        self.access_token = token

    def upload(self, file: File) -> None: ...
```

It is also possible to use django settings in factories.

```python title="mysite/polls/services/github_client.py"
@dataclass
class GithubClient:
    api_key: str
```


```python title="mysite/polls/services/factories.py"
from wireup import service


@service
def github_client_factory() -> GithubClient:
    return GithubClient(settings.GH_API_KEY)
```

### Use in views
```python title="app/views.py"
from wireup import container


@container.autowire
def upload_file_view(request: HttpRequest, s3_manager: S3Manager) -> HttpResponse:
    return HttpResponse(...)
```

Class-based views are also supported. You can autowire the `__init__` or the handler method as necessary. 


For more examples see the [Wireup Django integration tests](https://github.com/maldoinc/wireup/tree/master/test/integration/django).


## Api Reference

* [django_integration](../class/django_integration.md)
