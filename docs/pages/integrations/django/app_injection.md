---
description: Use inject_app for Django app-level dependency injection in commands, signals, checks, and script entry points outside request scope.
---

# App-Level Injection

Use `@inject_app` for Django callables that run outside the request/response lifecycle.

Such as:

- Management commands
- Signal handlers
- System checks
- Startup or script entry points after `django.setup()`

Use `@inject` for request handlers (Django views, DRF handlers, Ninja endpoints).

## Django 6 Background Tasks

Django 6 background tasks also run outside the request lifecycle, so they should use `@inject_app`.

```python title="myapp/tasks.py"
from django.tasks import task
from wireup import Injected
from wireup.integration.django import inject_app

from myapp.services import EmailService


@task
@inject_app
def send_welcome_email(user_id: int, email: Injected[EmailService]) -> None:
    email.send_welcome(user_id)
```

You can enqueue the task from a view or service as usual:

```python title="myapp/views.py"
from django.http import HttpResponse

from myapp.tasks import send_welcome_email


def signup_complete(request):
    send_welcome_email.enqueue(request.user.id)
    return HttpResponse("queued")
```

This uses the application/root container rather than the request-scoped container, which is the correct behavior for
work that executes after the request path.

## Management Commands

```python title="myapp/management/commands/greet.py"
from django.core.management.base import BaseCommand
from wireup import Injected
from wireup.integration.django import inject_app

from myapp.services import GreeterService


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--name", default="World")

    @inject_app
    def handle(
        self, *args, name: str, greeter: Injected[GreeterService], **options
    ):
        self.stdout.write(greeter.greet(name))
```

## Signal Handlers

```python title="myapp/signals.py"
from django.db.models.signals import post_save
from django.dispatch import receiver
from wireup import Injected
from wireup.integration.django import inject_app

from myapp.models import User
from myapp.services import WelcomeEmailService


@receiver(post_save, sender=User)
@inject_app
def on_user_created(
    sender,
    instance: User,
    created: bool,
    welcome: Injected[WelcomeEmailService],
    **kwargs,
):
    if created:
        welcome.send(instance.email)
```

## Django System Checks

```python title="myapp/checks.py"
from django.core.checks import Error, register
from wireup import Injected
from wireup.integration.django import inject_app

from myapp.services import HealthcheckService


@register()
@inject_app
def check_dependencies(
    app_configs,
    health: Injected[HealthcheckService],
    **kwargs,
):
    return [] if health.ok() else [Error("HealthcheckService is not healthy")]
```

## Script Entry Points

```python title="scripts/reindex.py"
import os
import django
from wireup import Injected
from wireup.integration.django import inject_app

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from myapp.services import ReindexService


@inject_app
def run(service: Injected[ReindexService]) -> None:
    service.reindex_all()


if __name__ == "__main__":
    run()
```

## Testing

See [Django Testing](testing.md) for command testing, dependency overrides, and request-handler tests.
