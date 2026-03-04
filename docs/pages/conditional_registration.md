# Conditional Registration

Wireup does not own your registration strategy. It only consumes whatever you pass in `injectables=[...]`.

That means you can build the list yourself based on environment, feature flags, or deployment mode, then hand the final
list to Wireup.

Once the container is created, Wireup runs the same startup validation guarantees on the final graph.

## Bundle + If Pattern

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

## Why Use This Pattern

* No new DSL to learn. Registration composition stays pure Python.
* Composition stays explicit and local to app bootstrap.
* Wireup remains environment-agnostic.
* Validation still happens at startup for the graph you actually run.

For reusable sub-graphs with runtime parameters, see [Factories: Reusable Factory Bundles](factories.md#reusable-factory-bundles).
