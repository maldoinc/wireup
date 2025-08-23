import click
import pytest
import wireup
from click.testing import CliRunner
from typing_extensions import Annotated
from wireup import Inject, Injected, service
from wireup.integration import click as wireup_click


@service
class NumberGenerator:
    def get_lucky_number(self) -> int:
        return 42


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def container() -> wireup.SyncContainer:
    return wireup.create_sync_container(
        services=[NumberGenerator], parameters={"env": "test", "debug": True, "name": "test-app"}
    )


def test_injects_dependencies(runner: CliRunner, container: wireup.SyncContainer) -> None:
    @click.group()
    def cli() -> None:
        pass

    @cli.command()
    def lucky_number(generator: Injected[NumberGenerator]) -> None:  # type: ignore[reportUnusedFunction]
        click.echo(str(generator.get_lucky_number()))

    wireup_click.setup(container, cli)
    result = runner.invoke(cli, ["lucky-number"])
    assert result.exit_code == 0
    assert result.output.strip() == "42"


def test_injects_parameters(runner: CliRunner, container: wireup.SyncContainer) -> None:
    @click.group()
    def cli() -> None:
        pass

    @cli.command()
    def show_env(  # type: ignore[reportUnusedFunction]
        env: Annotated[str, Inject(param="env")],
        debug: Annotated[bool, Inject(param="debug")],
        name: Annotated[str, Inject(param="name")],
    ) -> None:
        click.echo(f"{name} running in {env} with debug={debug}")

    wireup_click.setup(container, cli)
    result = runner.invoke(cli, ["show-env"])
    assert result.exit_code == 0
    assert result.output.strip() == "test-app running in test with debug=True"


def test_injects_nested_commands(runner: CliRunner, container: wireup.SyncContainer) -> None:
    @click.group()
    def cli() -> None:
        pass

    @click.group()
    def nested() -> None:
        pass

    cli.add_command(nested)

    @nested.command()
    def lucky_number(generator: Injected[NumberGenerator]) -> None:  # type: ignore[reportUnusedFunction]
        click.echo(str(generator.get_lucky_number()))

    wireup_click.setup(container, cli)
    result = runner.invoke(cli, ["nested", "lucky-number"])
    assert result.exit_code == 0
    assert result.output.strip() == "42"


def test_container_access(container: wireup.SyncContainer) -> None:
    @click.group()
    def cli() -> None:
        pass

    wireup_click.setup(container, cli)
    assert wireup_click.get_app_container(cli) == container  # type: ignore[reportAttributeAccessIssue]


def test_injects_command_options(runner: CliRunner, container: wireup.SyncContainer) -> None:
    @click.group()
    def cli() -> None:
        pass

    @cli.command()
    @click.option("--message", default="Your lucky number is")
    def lucky_number(generator: Injected[NumberGenerator], message: str) -> None:  # type: ignore[reportUnusedFunction]
        num = generator.get_lucky_number()
        click.echo(f"{message}: {num}")

    wireup_click.setup(container, cli)
    result = runner.invoke(cli, ["lucky-number"])
    assert result.exit_code == 0
    assert result.output.strip() == "Your lucky number is: 42"

    result = runner.invoke(cli, ["lucky-number", "--message", "The number"])
    assert result.exit_code == 0
    assert result.output.strip() == "The number: 42"


def test_get_container(runner: CliRunner, container: wireup.SyncContainer) -> None:
    @click.group()
    def cli() -> None:
        pass

    @cli.command()
    @click.option("--message", default="Your lucky number is")
    def lucky_number(message: str) -> None:  # type: ignore[reportUnusedFunction]
        generator = wireup_click.get_app_container(cli).get(NumberGenerator)
        num = generator.get_lucky_number()
        click.echo(f"{message}: {num}")

    wireup_click.setup(container, cli)
    result = runner.invoke(cli, ["lucky-number"])
    assert result.exit_code == 0
    assert result.output.strip() == "Your lucky number is: 42"
