Dependency injection for Django is available via the provided integration in `wireup.integration.django`.

## Installation

To install the integration, add `wireup.integration.django` to `INSTALLED_APPS` and define a new `WIREUP` setting.

```python title="settings.py"
import os
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

# Additional application settings.
S3_BUCKET_ACCESS_TOKEN = os.environ["S3_BUCKET_ACCESS_TOKEN"]
```


## Usage

### Define some services

```python title="mysite/polls/services/s3_manager.py"
from wireup import service


@service
@dataclass
class S3Manager:
    # Reference configuration by name.
    # This is the same name this appears in settings.
    access_token: Annotated[str, Inject(param="S3_BUCKET_ACCESS_TOKEN")]

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


def upload_file_view(request: HttpRequest, s3_manager: S3Manager) -> HttpResponse:
    return HttpResponse(...)
```

Class-based views are also supported, you can specify dependencies in your class' `__init__` function. 


For more examples see the [Wireup Django integration tests](https://github.com/maldoinc/wireup/tree/master/test/integration/django/view.py).


## Api Reference

* [django_integration](../class/django_integration.md)
