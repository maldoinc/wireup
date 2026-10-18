from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any, TypeVar

from typing_extensions import ParamSpec

import wireup
import wireup.ioc
import wireup.ioc.util
from wireup._wrapper_compiler import compile_injection_wrapper
from wireup.errors import WireupError
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.util import (
    ensure_is_type,
    get_globals,
    get_inject_annotated_parameters,
    get_valid_injection_annotated_parameters,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
    from wireup.ioc.container.sync_container import ScopedSyncContainer
    from wireup.ioc.types import AnnotatedParameter

P = ParamSpec("P")
R = TypeVar("R")


def _get_evaluated_signature(target: Callable[..., Any]) -> inspect.Signature:
    try:
        signature = inspect.signature(target)
        return signature.replace(
            parameters=[
                param.replace(
                    annotation=ensure_is_type(param.annotation, globalns_supplier=lambda: get_globals(target))
                )
                for param in signature.parameters.values()
            ],
            return_annotation=ensure_is_type(
                signature.return_annotation, globalns_supplier=lambda: get_globals(target)
            ),
        )
    except WireupError as exc:
        msg = f"Error evaluating annotations for {target!r}. {exc!s}"
        raise WireupError(msg) from exc
    except (NameError, TypeError, SyntaxError) as exc:
        msg = (
            f"Error evaluating annotations for {target!r}. Got {type(exc).__name__}: {exc!s}. "
            "Make sure the type is correctly imported and not inside a TYPE_CHECKING block.\n"
            "See: https://maldoinc.github.io/wireup/latest/future_annotations/"
        )
        raise WireupError(msg) from exc


def wrap_with_dependencies(target: Callable[P, R]) -> Callable[[Callable[..., Any]], Callable[P, R]]:
    """Preserve the target's metadata and combine its signature with the wrapper's dependency parameters.

    The wrapper must accept both ``*args`` and ``**kwargs``. Additional parameters must be keyword-only and must not
    share names with parameters of the target or an inner decorator. Injection is performed separately by the caller
    or framework integration. Unmarked parameters are supplied by the caller or use their defaults.

    :param target: The function being wrapped.
    """

    def _decorator(wrapper: Callable[..., Any]) -> Callable[P, R]:
        wrapper_sig = _get_evaluated_signature(wrapper)
        target_sig = _get_evaluated_signature(target)

        wrapper_params = list(wrapper_sig.parameters.values())
        if not all(
            any(param.kind == kind for param in wrapper_params)
            for kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ):
            msg = "wrap_with_dependencies wrapper must accept both *args and **kwargs."
            raise WireupError(msg)

        extra_params = [
            param
            for param in wrapper_params
            if param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        if any(param.kind != inspect.Parameter.KEYWORD_ONLY for param in extra_params):
            msg = "wrap_with_dependencies wrapper dependency parameters must be keyword-only."
            raise WireupError(msg)

        target_param_names = set(target_sig.parameters)
        collisions = sorted(param.name for param in extra_params if param.name in target_param_names)
        if collisions:
            msg = (
                "wrap_with_dependencies wrapper parameters must not conflict with a parameter of the wrapped callable "
                "or an inner decorator. "
                f"Conflicting parameter names: {', '.join(collisions)}"
            )
            raise WireupError(msg)

        target_params = list(target_sig.parameters.values())
        kwargs_params = [param for param in target_params if param.kind == inspect.Parameter.VAR_KEYWORD]
        signature = target_sig.replace(
            parameters=[
                *(param for param in target_params if param.kind != inspect.Parameter.VAR_KEYWORD),
                *extra_params,
                *kwargs_params,
            ],
        )
        wrapped = functools.wraps(target)(wrapper)
        wrapped.__signature__ = signature  # type: ignore[attr-defined]
        wrapped.__annotations__ = {
            param.name: param.annotation
            for param in signature.parameters.values()
            if param.annotation is not inspect.Parameter.empty
        }
        if signature.return_annotation is not inspect.Signature.empty:
            wrapped.__annotations__["return"] = signature.return_annotation
        return wrapped

    return _decorator


def _ensure_sync_container_target_is_sync(target: Callable[..., object]) -> None:
    if inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(target):
        msg = (
            "Sync container cannot perform injection on async targets. "
            "Create an async container via wireup.create_async_container."
        )
        raise WireupError(msg)


def inject_from_container_unchecked(
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer],
    *,
    hide_annotated_names: bool = False,
) -> Callable[[Callable[P, R]], Callable[..., R]]:
    """Inject dependencies into the decorated function. The "unchecked" part of the name refers to the fact that
    this cannot perform validation on the parameters to inject on module import time due to the absence of a container
    instance."""

    def _decorator(target: Callable[P, R]) -> Callable[..., R]:
        return inject_from_container_util(
            target=target,
            names_to_inject=get_inject_annotated_parameters(target),
            container=None,
            scoped_container_supplier=scoped_container_supplier,
            context_creator=None,
            hide_annotated_names=hide_annotated_names,
        )

    return _decorator


def inject_from_container(
    container: SyncContainer | AsyncContainer,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
    _context_creator: dict[Any, str] | None = None,
    *,
    hide_annotated_names: bool = False,
) -> Callable[[Callable[P, R]], Callable[..., R]]:
    """Inject dependencies into the decorated function based on annotations. Wireup containers will
    attempt to provide only parameters annotated with `Inject`.

    See the documentation for more details:
    https://maldoinc.github.io/wireup/latest/function_injection/

    :param container: The root container created via `wireup.create_sync_container` or
        `wireup.create_async_container`.
    :param scoped_container_supplier: An optional callable that returns the current scoped container instance.
        If provided, it will be used to create scoped dependencies. If not provided, the container will automatically
        enter a scope. Provide a scoped_container_supplier if you need to manage the container's scope manually.
    :param hide_annotated_names: If True, the parameters annotated with Wireup annotations will be removed from the
        signature of the decorated function.
    """

    def _decorator(target: Callable[P, R]) -> Callable[..., R]:
        if isinstance(container, SyncContainer):
            _ensure_sync_container_target_is_sync(target)

        return inject_from_container_util(
            target=target,
            names_to_inject=get_valid_injection_annotated_parameters(container, target),
            container=container,
            scoped_container_supplier=scoped_container_supplier,
            context_creator=_context_creator,
            hide_annotated_names=hide_annotated_names,
        )

    return _decorator


def inject_from_container_util(  # noqa: PLR0913
    target: Callable[P, R],
    names_to_inject: dict[str, AnnotatedParameter],
    container: SyncContainer | AsyncContainer | None,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
    context_creator: dict[Any, str] | None = None,
    *,
    hide_annotated_names: bool,
) -> Callable[..., R]:
    if not (container or scoped_container_supplier):
        msg = "Container or scoped_container_supplier must be provided for injection."
        raise WireupError(msg)

    if not names_to_inject:
        return target

    res = compile_injection_wrapper(
        target=target,
        names_to_inject=names_to_inject,
        container=container,
        scoped_container_supplier=scoped_container_supplier,
        context_creator=context_creator,
    )
    wrapped = res

    if hide_annotated_names:
        wireup.ioc.util.hide_annotated_names(wrapped)

    return wrapped
