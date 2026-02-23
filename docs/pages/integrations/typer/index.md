# Typer Integration

Dependency injection for Typer is available in the `wireup.integration.typer` module.

### Initialize the integration

First, [create a container](../../container.md), add your Typer commands, and then initialize the integration.

```python
import typer
import wireup

from wireup import Injected

app = typer.Typer()


@app.command()
def random_number(random: Injected[RandomService]) -> None:
    typer.echo(f"Your lucky number is: {random.get_random()}")


container = wireup.create_sync_container(injectables=[RandomService, services])
wireup.integration.typer.setup(container, app)
```

`setup` must be called after all commands (including nested groups) have been added.

### Inject in Typer Commands

Use `Injected[T]` or `Annotated[T, Inject(...)]` in command signatures.

```python
from typing import Annotated
from wireup import Inject


@app.command()
def env_info(
    env: Annotated[str, Inject(config="env")],
    debug: Annotated[bool, Inject(config="debug")],
) -> None:
    typer.echo(f"Environment: {env}")
    typer.echo(f"Debug mode: {debug}")
```

Injected parameters are hidden from CLI help automatically.

### Accessing the Container

```python
from wireup.integration.typer import get_app_container

container = get_app_container(app)
```

### API Reference

Visit [API Reference](../../class/typer_integration.md) for detailed information about the Typer integration module.
