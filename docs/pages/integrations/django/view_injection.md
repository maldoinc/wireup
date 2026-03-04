---
description: Inject dependencies in Django request handlers with inject across core views, DRF, Ninja, forms, and request-scoped services.
---

# Inject in Views

Use `@inject` for request-scoped Django callables.

This includes:

- Core Django function-based and class-based views
- DRF endpoints
- Django Ninja endpoints
- Forms or model methods that execute during a request

For non-request entry points (commands, signals, checks, scripts), use `@inject_app`:
[App-Level Injection](app_injection.md).

## Core Django Views

=== "Function-based view (sync)"

    ```python title="views.py"
    from django.http import HttpRequest, HttpResponse
    from wireup import Injected
    from wireup.integration.django import inject

    from myapp.services import GreeterService


    @inject
    def greet(
        request: HttpRequest, greeter: Injected[GreeterService]
    ) -> HttpResponse:
        name = request.GET.get("name", "World")
        return HttpResponse(greeter.greet(name))
    ```

=== "Function-based view (async)"

    ```python title="views.py"
    from django.http import HttpRequest, HttpResponse
    from wireup import Injected
    from wireup.integration.django import inject

    from myapp.services import AsyncGreeterService


    @inject
    async def greet(
        request: HttpRequest, greeter: Injected[AsyncGreeterService]
    ) -> HttpResponse:
        name = request.GET.get("name", "World")
        return HttpResponse(await greeter.agreet(name))
    ```

=== "Class-based view"

    ```python title="views.py"
    from django.http import HttpRequest, HttpResponse
    from django.views import View
    from wireup import Injected
    from wireup.integration.django import inject

    from myapp.services import GreeterService


    class GreetingView(View):
        @inject
        def get(
            self,
            request: HttpRequest,
            greeter: Injected[GreeterService],
        ) -> HttpResponse:
            name = request.GET.get("name", "World")
            return HttpResponse(greeter.greet(name))
    ```

## Django REST Framework

DRF handlers should use `@inject` explicitly.

```python title="drf_views.py"
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from wireup import Injected
from wireup.integration.django import inject

from myapp.services import GreeterService


@api_view(("GET",))
@inject
def drf_function_view(
    request: Request, greeter: Injected[GreeterService]
) -> Response:
    name = request.query_params.get("name", "World")
    return Response({"message": greeter.greet(name)})


class GreetingAPIView(APIView):
    @inject
    def get(
        self, request: Request, greeter: Injected[GreeterService]
    ) -> Response:
        name = request.query_params.get("name", "World")
        return Response({"message": greeter.greet(name)})


class GreetingViewSet(ViewSet):
    @inject
    def list(
        self, request: Request, greeter: Injected[GreeterService]
    ) -> Response:
        name = request.query_params.get("name", "World")
        return Response({"message": greeter.greet(name)})
```

## Django Ninja

Ninja handlers should also use `@inject` explicitly.

```python title="ninja_views.py"
from ninja import Router, Schema
from wireup import Injected
from wireup.integration.django import inject

from myapp.services import GreeterService


router = Router()


class ItemSchema(Schema):
    name: str
    price: float


@router.get("/greet")
@inject
def greet(request, name: str, greeter: Injected[GreeterService]):
    return {"greeting": greeter.greet(name)}


@router.post("/items")
@inject
def create_item(request, data: ItemSchema, greeter: Injected[GreeterService]):
    return {
        "name": data.name,
        "price": data.price,
        "message": greeter.greet(data.name),
    }
```

## Forms and Model Methods

If the callable runs during a request, use `@inject`.

```python title="forms.py"
from django import forms
from wireup import Injected
from wireup.integration.django import inject

from myapp.services import UserService


class UserRegistrationForm(forms.Form):
    username = forms.CharField()

    @inject
    def __init__(self, *args, user_service: Injected[UserService], **kwargs):
        super().__init__(*args, **kwargs)
        self.user_service = user_service

    def clean_username(self):
        username = self.cleaned_data["username"]
        if self.user_service.is_taken(username):
            raise forms.ValidationError("Username taken")
        return username
```

## Request Object Injection

The current `HttpRequest` is available as a `scoped` dependency.

```python title="services/auth.py"
from django.http import HttpRequest
from wireup import injectable


@injectable(lifetime="scoped")
class AuthService:
    def __init__(self, request: HttpRequest) -> None:
        self.request = request
```

## Testing

See [Django Testing](testing.md) for request-handler tests, async testing with `AsyncClient`, and dependency overrides.
