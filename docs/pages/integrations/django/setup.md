# Django Setup and Installation

This page focuses on installation and integration setup details.

## 1. Install Wireup

```bash
pip install wireup
```

## 2. Register the Django integration app

Add `wireup.integration.django` to `INSTALLED_APPS`.

```python title="settings.py"
INSTALLED_APPS = [
    # ...existing apps...
    "wireup.integration.django",
]
```

## 3. Add Wireup middleware

Add `wireup.integration.django.wireup_middleware` to `MIDDLEWARE`.

```python title="settings.py"
MIDDLEWARE = [
    "wireup.integration.django.wireup_middleware",
    # ...existing middleware...
]
```

Keep this middleware near the start of your middleware list so request-scoped dependencies are available early in the
request lifecycle.

## 4. Configure `WIREUP`

```python title="settings.py"
from wireup.integration.django import WireupSettings

WIREUP = WireupSettings(
    injectables=["mysite.services"],
    # Recommended: use explicit @inject for Django/DRF/Ninja views.
    # Set to True only if you want automatic injection for core Django views.
    auto_inject_views=False,
)
```

`injectables` should include modules that contain `@injectable` registrations.

Use `@inject` on request handlers (Django views, DRF handlers, Ninja endpoints), and `@inject_app` on non-request
entry points (management commands, signals, checks). If `auto_inject_views=True`, automatic injection applies to core
Django views only.

## 5. Django settings as Wireup config

The Django integration exposes settings values as Wireup config keys.

```python title="settings.py"
S3_BUCKET_TOKEN = "secret-token"
```

```python title="myapp/services/s3_manager.py"
from typing import Annotated
from wireup import Inject, injectable


@injectable
class S3Manager:
    def __init__(
        self,
        token: Annotated[str, Inject(config="S3_BUCKET_TOKEN")],
    ) -> None:
        self.token = token
```

The value is read from Django settings during app startup.

If you prefer to keep domain objects free of Wireup annotations, inject settings in a factory instead:

```python title="myapp/services/factories.py"
from django.conf import settings
from wireup import injectable


class S3Manager:
    def __init__(self, token: str) -> None:
        self.token = token


@injectable
def s3_manager_factory() -> S3Manager:
    return S3Manager(token=settings.S3_BUCKET_TOKEN)
```

## 6. Verify setup

1. Start Django: `python manage.py runserver`
2. Hit a view that uses `@inject`
3. Confirm injected service behavior

If you see errors about `HttpRequest` availability, verify `wireup_middleware` is configured.
