Dependency injection for Django is available via the first-party integration wireup provides, available in
`wireup.integration.django_integration`.

**Features:**

* Automatically decorate views
    * Removes the need for `@container.autowire`.
* Expose Django configuration in the container's parameters.

## Installation

To install the integration, add `WireupMiddleware` to the list of middlewares and define a new "WIREUP" setting.

This will automatically register settings as parameters with the same name, perform autowiring 
in views and [warmup the container](../optimizing_container.md).

```python title="settings.py"
MIDDLEWARE = [
    ...,
    # Add the wireup integration middleware
    "wireup.integration.django_integration.WireupMiddleware"
]

WIREUP = {
    # This is a list of top-level modules containing application services.
    # It can be either a list of strings or module types
    "SERVICE_MODULES": ["test.integration.django.service"]
},
```


## Usage

### Define some services

```python title="app/services/s3_manager.py"
@container.register
class S3Manager:
    # Reference configuration by name.
    # This is the same name this appears in settings.
    def __init__(self, token: Annotated[str, Wire(parameter="S3_BUCKET_ACCESS_TOKEN")]):
        self.access_token = token

    def upload(self, file: File) -> None: ...
```

### Use in views
```python title="app/views.py"
# s3_manager is automatically injected by wireup based on the annotated type.
def upload_file(request: HttpRequest, s3_manager: S3Manager) -> HttpResponse:
    return HttpResponse(...)

```

For more examples see the [Wireup Django integration tests](https://github.com/maldoinc/wireup/tree/master/test/integration/django).


## Api Reference

* [django_integration](../class/django_integration.md)
