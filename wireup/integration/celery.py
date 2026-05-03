from __future__ import annotations

from contextvars import ContextVar, Token
from threading import Lock
from typing import TYPE_CHECKING, Any

from celery.signals import task_postrun, task_prerun, worker_process_shutdown, worker_shutdown

from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.util import hide_annotated_names

if TYPE_CHECKING:
    from collections.abc import Callable

    from celery import Celery
    from celery.app.task import Task

    from wireup.ioc.container.sync_container import ScopedSyncContainer, SyncContainer

_task_container_ctx: ContextVar[ScopedSyncContainer] = ContextVar("wireup_celery_task_container")
_active_task_scopes: dict[str, tuple[Any, Token[ScopedSyncContainer]]] = {}
_active_task_scopes_lock = Lock()


def _mark_task_as_injected(target: Any) -> Any:
    target._wireup_celery_injected = True  # type: ignore[reportAttributeAccessIssue]
    return target


def _inject_task_function(fn: Callable[..., Any]) -> Callable[..., Any]:
    hide_annotated_names(fn)
    wrapped = inject_from_container_unchecked(get_task_container, hide_annotated_names=False)(fn)
    return _mark_task_as_injected(wrapped)


def inject(target: Any) -> Any:
    """Inject dependencies into a Celery task function or task instance.

    Use this decorator on every task that needs Wireup dependency injection.
    """
    if callable(target) and not hasattr(target, "run"):
        return _inject_task_function(target)

    run = getattr(target, "run", None)
    if callable(run):
        target.run = _inject_task_function(run)
        if hasattr(target, "app") and hasattr(target, "__header__"):
            target.__header__ = target.app.type_checker(target.run, bound=False)
        return _mark_task_as_injected(target)

    msg = "@wireup.integration.celery.inject expects a callable task function or a Celery task object."
    raise WireupError(msg)


def get_app_container(app: Celery) -> SyncContainer:
    """Return the container associated with the given Celery application."""
    return app.wireup_container  # type: ignore[reportAttributeAccessIssue]


def get_task_container() -> ScopedSyncContainer:
    """Return the scoped container handling the current task execution."""
    msg = "Task container in Wireup is only available during a Celery task execution."
    try:
        return _task_container_ctx.get()
    except LookupError as e:
        raise WireupError(msg) from e


def _is_wireup_injected_task(task: Task) -> bool:
    return bool(getattr(task, "_wireup_celery_injected", False) or getattr(task.run, "_wireup_celery_injected", False))


def setup(container: SyncContainer, app: Celery) -> None:
    """Integrate Wireup with Celery.

    Setup stores the app container and manages task scope context via Celery task lifecycle signals.
    Tasks must be decorated with `@wireup.integration.celery.inject` to use dependency injection.
    """
    app.wireup_container = container  # type: ignore[reportAttributeAccessIssue]

    if getattr(app, "_wireup_celery_signals_registered", False):
        return

    def _task_prerun(*_args: object, **kwargs: object) -> None:
        task = kwargs.get("task") or kwargs.get("sender")
        task_id = kwargs.get("task_id")
        if not task or not task_id:
            return
        if getattr(task, "app", None) is not app or not _is_wireup_injected_task(task):
            return

        scope_ctx = container.enter_scope()
        scoped_container = scope_ctx.__enter__()
        token = _task_container_ctx.set(scoped_container)
        with _active_task_scopes_lock:
            _active_task_scopes[str(task_id)] = (scope_ctx, token)

    def _task_postrun(*_args: object, **kwargs: object) -> None:
        task_id = kwargs.get("task_id")
        if not task_id:
            return

        scope_ctx = None
        token = None
        with _active_task_scopes_lock:
            scope_state = _active_task_scopes.pop(str(task_id), None)
            if scope_state:
                scope_ctx, token = scope_state

        if not scope_ctx or token is None:
            return

        try:
            _task_container_ctx.reset(token)
        finally:
            scope_ctx.__exit__(None, None, None)

    def _close_container(*_args: object, **_kwargs: object) -> None:
        container.close()

    task_prerun.connect(_task_prerun, weak=False)
    task_postrun.connect(_task_postrun, weak=False)
    worker_process_shutdown.connect(_close_container, weak=False)
    worker_shutdown.connect(_close_container, weak=False)
    app._wireup_celery_signals_registered = True  # type: ignore[reportAttributeAccessIssue]
