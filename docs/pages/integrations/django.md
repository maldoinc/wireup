Dependency injection for Django is available via the first-party integration wireup provides, available in
`wireup.integration.django_integration`.

**Features:**

* Automatically decorate views.
* Expose Django configuration in the container's parameters.

## Installation

To install the integration, add `WireupMiddleware` to the list of middlewares and define a setting
`WIREUP_SERVICE_MODULES` containing a list of modules (not strings!) with application services.

This will automatically register settings as parameters with the same name, perform autowiring 
in views and [warmup the container](../optimizing_container.md).

```python title="settings.py"
MIDDLEWARE = [
    ...,
    # Add the wireup integration middleware
    "wireup.integration.django_integration.WireupMiddleware"
]
WIREUP_SERVICE_MODULES=[service]
```


## Usage

### Define some services
```python title="app/services/greeter_service.py"
class GreeterService:
    # reference configuration by name.
    def __init__(self, default_locale: Annotated[str, Wire(parameter="LANGUAGE_CODE")]):
        self.default_locale = default_locale
    
    def greet(self) -> str:
      return ...
```

### Use in views
```python title="views.py"
@require_GET
def greet_view(request: HttpRequest, greeter: GreeterService) -> HttpResponse:
    name = request.GET.get("name")

    return HttpResponse(greeter.greet(name))

```



## Api Reference

* [django_integration](../class/django_integration.md)
