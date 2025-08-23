# :simple-click: Click Integration

Dependency injection for Click is available in the `wireup.integration.click` module.

<div class="grid cards annotate" markdown>

-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Inject dependencies in Click commands and automatically manage container lifecycle.

-   :material-share-circle:{ .lg .middle } __Shared business logic__

    ---

    Wireup is framework-agnostic. Share the service layer between your CLI and other interfaces, such as a web application.

</div>

### Initialize the integration

To initialize the integration, call `wireup.integration.click.setup` after adding all commands and configuration.

```python
import click
from wireup import Inject, Injected, service

@click.group()
def cli():
    pass

container = wireup.create_sync_container(
    # service_modules is a list of top-level modules with service registrations
    service_modules=[services],
    parameters={
        "env": "development",
        "debug": True
    }
)

# Initialize the integration.
# Must be called after all commands have been added.
wireup.integration.click.setup(container, cli)
```

### Inject in Click Commands

To inject dependencies, add the type to the commands' signature and annotate them as necessary.
See [Annotations](../../annotations.md) for more details.

```python title="Click Command"
@cli.command()
def random_number(random: Injected[RandomService]):
    click.echo(f"Your lucky number is: {random.get_random()}")

@cli.command()
def env_info(
    env: Annotated[str, Inject(param="env")],
    debug: Annotated[bool, Inject(param="debug")]
):
    click.echo(f"Environment: {env}")
    click.echo(f"Debug mode: {debug}")
```

### Accessing the Container

To access the Wireup container directly, use the following:

```python
# Get application-wide container
from wireup.integration.click import get_app_container

container = get_app_container(cli)
```

### Testing

When testing Click commands with dependency injection, you can swap out services in your tests by overriding
services before executing the Click runner.

```python
def test_random_number_command(runner):
    test_container = wireup.create_sync_container(...)
    
    cli = click.Group()
    wireup.integration.click.setup(test_container, cli)
    
    with container.override.service(RandomService, new=mocked_random_service):
        result = runner.invoke(cli, ["random-number"])

    assert result.exit_code == 0
    assert "Your lucky number is:" in result.output
```

### API Reference

Visit [API Reference](../../class/click_integration.md) for detailed information about the Click integration module.
