# Proposal: Django Ninja Integration for Wireup

## Background

Wireup currently supports several web frameworks including FastAPI, Flask, Django, and Starlette. Django Ninja is a popular Django-based API framework that shares many design principles with FastAPI (Pydantic schemas, type hints for parameter parsing) but runs on Django.

While Wireup has Django integration, it doesn't work out-of-the-box with Django Ninja route handlers due to how Ninja inspects function signatures.

## The Problem

Django Ninja uses function signature introspection to determine how to parse request parameters:

```python
@router.post("/items/")
def create_item(request, data: ItemSchema, page: int = 1):
    #                        ↑ Body param    ↑ Query param
```

When a Wireup-injected service appears in the signature:

```python
@router.post("/items/")
def create_item(request, data: ItemSchema, service: Injected[ItemService]):
    #                                       ↑ Ninja tries to parse this as Body
```

Ninja attempts to generate a Pydantic schema for `ItemService`, which fails with:

```
PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <class 'ItemService'>
```

### Why This Happens

1. Ninja's `ViewSignature` class inspects the function via `inspect.signature()`
2. For each parameter, it checks if it's a path param, has an explicit `Param` annotation, is a Pydantic model, etc.
3. Non-primitive types without explicit markers are treated as `Body` parameters
4. Pydantic then tries (and fails) to generate a schema for the service class

**Source references:**

- `ViewSignature.__init__` calls `get_typed_signature(self.view_func)` which wraps `inspect.signature()`:
  https://github.com/vitalik/django-ninja/blob/master/ninja/signature/details.py#L47-L52

- `_get_param_type` determines parameter source (Body, Query, Path, etc.):
  https://github.com/vitalik/django-ninja/blob/master/ninja/signature/details.py#L219-L300

- The fallback logic that treats unknown types as Body params:
  https://github.com/vitalik/django-ninja/blob/master/ninja/signature/details.py#L284-L289

### Why FastAPI Works But Ninja Doesn't

FastAPI has native `Depends()` support that Wireup hooks into:

```python
# wireup/_annotations.py - FastAPI special handling
def Inject(...) -> InjectableType:
    ...
    # Wraps with FastAPI's Depends() so FastAPI knows to skip schema generation
    return importlib.import_module("fastapi").Depends(_inner)
```

**Source:** https://github.com/maldoinc/wireup/blob/master/wireup/_annotations.py#L53-L61

Django Ninja doesn't have an equivalent `Depends()` mechanism.

## Proposed Solution

Create a `@inject` decorator for Django Ninja that:

1. Identifies parameters annotated with `Injected[T]` (or `Annotated[T, Inject()]`)
2. Modifies the function's `__signature__` to exclude those parameters
3. Resolves dependencies from the Wireup container at runtime

### Implementation

```python
# wireup/integration/django/ninja.py

import inspect
from functools import wraps
from typing import Annotated, Any, Callable, TypeVar, get_args, get_origin

from wireup.integration.django import get_request_container
from wireup.ioc.types import InjectableType

F = TypeVar("F", bound=Callable[..., Any])


def _is_injectable(annotation: Any) -> bool:
    """Check if annotation uses Wireup's Injected[T] or Annotated[T, Inject()]."""
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        return any(isinstance(arg, InjectableType) for arg in args[1:])
    return False


def inject(func: F) -> F:
    """
    Decorator for Django Ninja views that enables Wireup dependency injection.
    
    Django Ninja inspects function signatures to determine request parameters.
    This decorator hides Wireup-injectable parameters from Ninja's introspection
    and resolves them from the container at runtime.
    
    Usage:
        from wireup import Injected
        from wireup.integration.django.ninja import inject
        
        @router.post("/items/")
        @inject
        def create_item(
            request,
            data: ItemSchema,
            service: Injected[ItemService],
        ):
            return service.create(data)
    
    Note:
        Place @inject below @router.* decorators.
    """
    sig = inspect.signature(func)
    
    # Find parameters marked for injection
    injectable_params = {
        name: param
        for name, param in sig.parameters.items()
        if _is_injectable(param.annotation)
    }
    
    # Create signature without injectable params (Ninja only sees this)
    visible_params = [
        p for p in sig.parameters.values() 
        if p.name not in injectable_params
    ]
    
    @wraps(func)
    def wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
        container = get_request_container()
        
        # Resolve dependencies
        for name, param in injectable_params.items():
            actual_type = get_args(param.annotation)[0]
            kwargs[name] = container.get(actual_type)
        
        return func(request, *args, **kwargs)
    
    wrapper.__signature__ = sig.replace(parameters=visible_params)
    return wrapper
```

### Why Modify `__signature__`?

Python's `inspect.signature()` checks for a `__signature__` attribute before falling back to introspection.

**Source:** https://docs.python.org/3/library/inspect.html#inspect.signature

> If the object has a `__signature__` attribute and if it is not None, it is used as the signature.

By setting this attribute, we control what Ninja sees:

```python
# What Ninja sees (modified signature):
(request, data: ItemSchema)

# What actually runs (original signature):
(request, data: ItemSchema, service: Injected[ItemService])
```

## Usage Example

```python
from ninja import Router
from wireup import Injected
from wireup.integration.django.ninja import inject

from myapp.services import ItemService
from myapp.schemas import ItemSchema, ItemResponse

router = Router()

@router.post("/items/", response=ItemResponse)
@inject
def create_item(
    request,
    data: ItemSchema,
    service: Injected[ItemService],
) -> ItemResponse:
    item = service.create(data)
    return ItemResponse.from_orm(item)
```

## Alternative Approaches Considered

### 1. Contribute `Depends()` to Django Ninja

Django Ninja could add a `Depends()` mechanism like FastAPI. However:
- This requires changes to Ninja itself
- Ninja's maintainers may have different design goals
- Would take longer to land

### 2. Use `**kwargs` to hide parameters

```python
def create_item(request, data: ItemSchema, **kwargs):
    service = get_container().get(ItemService)
```

Downsides:
- Loses type hints and IDE support
- Not declarative
- Requires manual container access

### 3. Class-based views with constructor injection

```python
class ItemView:
    def __init__(self, service: ItemService):
        self.service = service
```

Downsides:
- Doesn't match Ninja's function-based paradigm
- More boilerplate

## Testing Considerations

1. **Unit tests for the decorator:**
   - Verify `__signature__` is correctly modified
   - Verify injectable params are identified correctly
   - Verify non-injectable params are preserved

2. **Integration tests:**
   - Verify Ninja can register routes with `@inject`
   - Verify dependencies are resolved at request time
   - Verify scoped containers work correctly

3. **Edge cases:**
   - Multiple injectable params
   - Mixed injectable and non-injectable params
   - Async views (nice-to-have, not blocking)

## Documentation Updates

1. Add Django Ninja to the list of supported frameworks
2. Add usage example in the Django integration docs
3. Note the decorator placement requirement (`@inject` below `@router.*`)

## Design Decisions

1. **Scope:** This integration targets Django Ninja only. Class-based `api_controller` from django-ninja-extra is out of scope.

2. **Async support:** Nice to have but not a blocker for initial implementation. Can be added later if needed.

3. **Module path:** The decorator should be exposed from `wireup.integration.django.ninja` to keep it under the existing Django integration namespace.
