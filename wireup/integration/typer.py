from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup import SyncContainer, inject_from_container

if TYPE_CHECKING:
    from typer import Typer


def _inject_callback(container: SyncContainer, callback: Any) -> Any:
    if callback is None or not callable(callback):
        return callback

    return inject_from_container(container, hide_annotated_names=True)(callback)


def _inject_typer(container: SyncContainer, app: Typer) -> None:
    for command in app.registered_commands:
        command.callback = _inject_callback(container, command.callback)

    if app.registered_callback:
        app.registered_callback.callback = _inject_callback(container, app.registered_callback.callback)
        app.registered_callback.result_callback = _inject_callback(container, app.registered_callback.result_callback)

    for group in app.registered_groups:
        group.callback = _inject_callback(container, group.callback)
        group.result_callback = _inject_callback(container, group.result_callback)
        _inject_typer(container, group.typer_instance)


def setup(container: SyncContainer, app: Typer) -> None:
    """Integrate Wireup with Typer by injecting dependencies into command callbacks."""
    _inject_typer(container, app)
    app.wireup_container = container  # type: ignore[reportAttributeAccessIssue]


def get_app_container(app: Typer) -> SyncContainer:
    """Return the container associated with the given Typer application."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]
