Dependency injection for Django is available via the first-party integration wireup provides, available in
`wireup.integration.django_integration`.

**Features:**

* Automatically decorate views.
* Expose Django configuration in the container's parameters.

## Usage

### 0. Define some services
```python title="app/services/greeter_service.py"
class GreeterService:
    # reference configuration by name.
    def __init__(self, default_locale: Annotated[str, Wire(parameter="LANGUAGE_CODE")]):
        self.default_locale = default_locale
    
    def greet(self) -> str:
      return ...
```

### 1. Initialize the integration

```python title="wsgi.py"
from app import services

# Import the top level service module(s) and pass them to the integration.
# Execute this as the last statement in wsgi.py.
wireup_init_django_integration(service_modules=[services])
```

Next, add the wireup middleware. This will automatically perform injection in django views. 
If this step is omitted then the `@container.autowire` decorator must be used instead.
```python title="settings.py"
MIDDLEWARE = [
    ...,
    "wireup.integration.django_integration.WireupMiddleware",
]
```

### 2. Use in views
```python title="views.py"
@require_GET
def greet_view(request: HttpRequest, greeter: GreeterService) -> HttpResponse:
    name = request.GET.get("name")

    return HttpResponse(greeter.greet(name))

```



## Api Reference

* [django_integration](../class/django_integration.md)
