from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, AsyncGenerator, Generator

from wireup.errors import ContainerCloseError, WireupError

if TYPE_CHECKING:
    from types import TracebackType


def clean_exit_stack(
    exit_stack: list[Generator[Any, Any, Any] | AsyncGenerator[Any, Any]],
    exc_val: BaseException | None = None,
    exc_tb: TracebackType | None = None,
) -> None:
    if entry := [gen for gen in exit_stack if inspect.isasyncgen(gen)]:
        msg = (
            "The following generators are async factories and closing them with a SyncContainer is not possible. "
            "If you require async dependencies create an AsyncContainer via wireup.create_async_container instead. "
            f"List of async factories encountered: {entry}."
        )

        raise WireupError(msg)

    errors: list[Exception] = []

    for gen in reversed(exit_stack):
        try:
            if exc_val:
                gen.throw(exc_val)  # type: ignore[union-attr]
            else:
                gen.send(None)  # type: ignore[union-attr]
        except StopIteration:  # noqa: PERF203
            pass
        except Exception as e:  # noqa: BLE001
            if e is not exc_val:
                errors.append(e)

    maybe_raise_exc(exc_val=exc_val, exc_tb=exc_tb, container_close_errors=errors)


async def async_clean_exit_stack(
    exit_stack: list[Generator[Any, Any, Any] | AsyncGenerator[Any, Any]],
    exc_val: BaseException | None = None,
    exc_tb: TracebackType | None = None,
) -> None:
    errors: list[Exception] = []

    for gen in reversed(exit_stack):
        try:
            if inspect.isasyncgen(gen):
                if exc_val:
                    await gen.athrow(exc_val)
                else:
                    await gen.asend(None)
            elif exc_val:
                gen.throw(exc_val)  # type: ignore[union-attr]
            else:
                gen.send(None)  # type: ignore[union-attr]

        except StopIteration:  # noqa: PERF203
            pass
        except StopAsyncIteration:
            pass
        except Exception as e:  # noqa: BLE001
            if e is not exc_val:
                errors.append(e)

    maybe_raise_exc(exc_val=exc_val, exc_tb=exc_tb, container_close_errors=errors)


def maybe_raise_exc(
    *,
    exc_val: BaseException | None = None,
    exc_tb: TracebackType | None = None,
    container_close_errors: list[Exception] | None = None,
) -> None:
    if not exc_val:
        if container_close_errors:
            raise ContainerCloseError(container_close_errors)
        return

    if exc_tb is not None:
        exc_val.__traceback__ = exc_tb

    if container_close_errors:
        raise exc_val from ContainerCloseError(container_close_errors)

    raise exc_val
