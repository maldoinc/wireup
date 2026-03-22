Use reusable bundles when you need to register the same services more than once with different settings, such as
multiple database clients or tenant-specific integrations.

Use a function that returns injectable factories:

```python
from dataclasses import dataclass
from typing import Annotated

import wireup
from wireup import Inject, injectable


@dataclass
class DbClient:
    dsn: str


@dataclass
class DbRepository:
    client: DbClient


def make_db_bundle(*, dsn: str, qualifier: str | None = None) -> list[object]:
    @injectable(qualifier=qualifier)
    def db_client_factory() -> DbClient:
        return DbClient(dsn=dsn)

    @injectable(qualifier=qualifier)
    def db_repo_factory(
        client: Annotated[DbClient, Inject(qualifier=qualifier)],
    ) -> DbRepository:
        return DbRepository(client=client)

    return [db_client_factory, db_repo_factory]
```

Then create your container with multiple bundles:

```python

primary = make_db_bundle(dsn="postgresql://primary-db")
analytics = make_db_bundle(
    dsn="postgresql://analytics-db",
    qualifier="analytics",
)

container = wireup.create_sync_container(injectables=[*primary, *analytics])
```

Use an unqualified default (`None`) for your primary bundle, then add qualifiers only where needed:

```python
from typing import Annotated
from wireup import Inject, Injected, injectable


@injectable
class ReportService:
    def __init__(
        self,
        primary_repo: Injected[DbRepository],
        analytics_repo: Annotated[DbRepository, Inject(qualifier="analytics")],
    ) -> None:
        self.primary_repo = primary_repo
        self.analytics_repo = analytics_repo
```

## Why Use Bundles

- The setup stays in plain Python without Wireup-Specific syntax.
- It is easy to see what gets registered.
- The final graph is still validated when the container is created.
- You can combine this with [Conditional Registration](conditional_registration.md) when different environments need
  different bundles.
