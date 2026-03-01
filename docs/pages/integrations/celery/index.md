# Celery Integration

Dependency injection for Celery is available in the `wireup.integration.celery` module.

<div class="grid cards annotate" markdown>

- :material-cog-refresh:{ .lg .middle } __Explicit Dependency Injection__

    ______________________________________________________________________

    Task injection is opt-in via `@inject`.

- :material-share-circle:{ .lg .middle } __Shared Business Logic__

    ______________________________________________________________________

    Wireup is framework-agnostic. Share the same service layer between Celery workers, APIs, and CLIs.

</div>

### Initialize the integration

First, [create a sync container](../../container.md) with your dependencies:

```python
from celery import Celery
import wireup

celery_app = Celery("my_app")

container = wireup.create_sync_container(injectables=[services])
wireup.integration.celery.setup(container, celery_app)
```

### Inject in Celery Tasks

Tasks that need Wireup injection must be decorated with `@inject`.

```python title="Celery Task"
from wireup import Injected
from wireup.integration.celery import inject


@celery_app.task
@inject
def process_order(order_service: Injected[OrderService], order_id: str) -> None:
    order_service.process(order_id)
```

### Accessing the Container

To access the Wireup container directly, use:

```python
from wireup.integration.celery import get_app_container, get_task_container

# App-wide container created with wireup.create_sync_container
app_container = get_app_container(celery_app)

# Task-scoped container, available only while a task is running
task_container = get_task_container()
```

### API Reference

Visit [API Reference](../../class/celery_integration.md) for detailed information about the Celery integration module.
