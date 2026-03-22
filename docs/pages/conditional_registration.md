# Conditional Registration

Wireup does not use a special syntax for conditional registration. Build the `injectables` list in normal Python based
on environment, feature flags, or deployment mode, then pass the final list to the container.

Wireup still validates the final graph when the container is created.

## Bundle + If Statements

Use small bundle functions (or constants) and compose them with normal Python `if` statements.

```python
import os
import wireup

from my_app import services
from my_app.integrations import tracing
from my_app.integrations import metrics
from my_app.dev_tools import debug_panel


def core_bundle():
    return [services]


def observability_bundle():
    return [tracing, metrics]


def dev_bundle():
    return [debug_panel]


env = os.getenv("APP_ENV", "dev")
enable_observability = os.getenv("ENABLE_OBSERVABILITY") == "1"

injectables = [*core_bundle()]

if enable_observability:
    injectables.extend(observability_bundle())

if env == "dev":
    injectables.extend(dev_bundle())

container = wireup.create_sync_container(
    injectables=injectables,
    config={"env": env},
)
```

## Environment-Specific Implementations

You can also switch concrete implementations by choosing different bundles:

```python
import os
import wireup

from my_app.base import services
from my_app.cache_dev import injectables as cache_dev_bundle
from my_app.cache_prod import injectables as cache_prod_bundle

env = os.getenv("APP_ENV", "dev")

injectables = [services]

if env == "prod":
    injectables.extend(cache_prod_bundle)
else:
    injectables.extend(cache_dev_bundle)

container = wireup.create_sync_container(injectables=injectables)
```

## Single Dependency Swap: Mailer

For one-off swaps, keep it simple and choose one injectable with a plain `if`:

```python
import os
import wireup

from my_app.services import UserService
from my_app.mail.dev_mailer import ConsoleMailer
from my_app.mail.prod_mailer import SesMailer

env = os.getenv("APP_ENV", "dev")

injectables = [UserService]

if env == "prod":
    injectables.append(SesMailer)
else:
    injectables.append(ConsoleMailer)

container = wireup.create_sync_container(injectables=injectables)
```

## Why Do It This Way

- No new DSL to learn.
- Registration stays in plain Python.
- The final graph is still validated at startup.

For reusable sub-graphs with runtime parameters, see [Reusable Bundles](reusable_bundles.md).
