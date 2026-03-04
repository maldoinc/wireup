from typing import Optional

import pytest
import typer
import wireup
from typer.testing import CliRunner
from typing_extensions import Annotated
from wireup import Inject, Injected, injectable
from wireup.integration import typer as wireup_typer


@injectable
class NumberGenerator:
    def get_lucky_number(self) -> int:
        return 42


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def container() -> wireup.SyncContainer:
    return wireup.create_sync_container(
        injectables=[NumberGenerator], config={"env": "test", "debug": True, "name": "test-app"}
    )


def test_injects_dependencies(runner: CliRunner, container: wireup.SyncContainer) -> None:
    app = typer.Typer()

    @app.command()
    def lucky_number(generator: Injected[NumberGenerator]) -> None:  # type: ignore[reportUnusedFunction]
        typer.echo(str(generator.get_lucky_number()))

    wireup_typer.setup(container, app)

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert result.output.strip() == "42"


def test_injects_parameters(runner: CliRunner, container: wireup.SyncContainer) -> None:
    app = typer.Typer()

    @app.command()
    def show_env(  # type: ignore[reportUnusedFunction]
        env: Annotated[str, Inject(config="env")],
        debug: Annotated[bool, Inject(config="debug")],
        name: Annotated[str, Inject(config="name")],
    ) -> None:
        typer.echo(f"{name} running in {env} with debug={debug}")

    wireup_typer.setup(container, app)

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert result.output.strip() == "test-app running in test with debug=True"


def test_injects_nested_commands(runner: CliRunner, container: wireup.SyncContainer) -> None:
    app = typer.Typer()
    nested = typer.Typer()
    app.add_typer(nested, name="nested")

    @nested.command()
    def lucky_number(generator: Injected[NumberGenerator]) -> None:  # type: ignore[reportUnusedFunction]
        typer.echo(str(generator.get_lucky_number()))

    wireup_typer.setup(container, app)

    result = runner.invoke(app, ["nested", "lucky-number"])
    assert result.exit_code == 0
    assert result.output.strip() == "42"


def test_hides_injected_parameters_from_help(runner: CliRunner, container: wireup.SyncContainer) -> None:
    app = typer.Typer()

    @app.command()
    def lucky_number(  # type: ignore[reportUnusedFunction]
        generator: Injected[NumberGenerator],
        message: Optional[str] = typer.Option("Your lucky number is", "--message"),
    ) -> None:
        typer.echo(f"{message}: {generator.get_lucky_number()}")

    wireup_typer.setup(container, app)

    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    assert "--message" in help_result.output
    assert "generator" not in help_result.output

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert result.output.strip() == "Your lucky number is: 42"


def test_container_access(container: wireup.SyncContainer) -> None:
    app = typer.Typer()

    wireup_typer.setup(container, app)
    assert wireup_typer.get_app_container(app) == container  # type: ignore[reportAttributeAccessIssue]


def test_get_container_inside_command(runner: CliRunner, container: wireup.SyncContainer) -> None:
    app = typer.Typer()

    @app.command()
    def lucky_number(message: str = "Your lucky number is") -> None:  # type: ignore[reportUnusedFunction]
        generator = wireup_typer.get_app_container(app).get(NumberGenerator)
        typer.echo(f"{message}: {generator.get_lucky_number()}")

    wireup_typer.setup(container, app)

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert result.output.strip() == "Your lucky number is: 42"
