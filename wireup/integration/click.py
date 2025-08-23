from click import Group

from wireup import SyncContainer, inject_from_container


def _inject_commands(container: SyncContainer, group: Group) -> None:
    for command in group.commands.values():
        if fn := command.callback:
            command.callback = inject_from_container(container)(fn)

        if isinstance(command, Group):
            _inject_commands(container, command)


def setup(container: SyncContainer, command: Group) -> None:
    """Integrate Wireup with Click by injecting dependencies into Click commands.

    :command: The Click command group to inject dependencies into
    """
    _inject_commands(container, command)
    command.wireup_container = container  # type: ignore[reportAttributeAccessIssue]


def get_app_container(app: Group) -> SyncContainer:
    """Retrieve the Wireup container associated with a Click command group."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]
