from __future__ import annotations

from typing import TYPE_CHECKING

from wireup.errors import ContainerCloseError, WireupError

if TYPE_CHECKING:
    from types import TracebackType

    from wireup.ioc.types import ExitStack


_CONTAINER_CLOSE_ERR = "The following exceptions were raised while closing of container"


def clean_exit_stack(
    exit_stack: ExitStack,
    exc_val: BaseException | None = None,
    exc_tb: TracebackType | None = None,
) -> None:
    if entry := [gen for gen, is_async in exit_stack if is_async]:
        msg = (
            "The following generators are async factories and closing them with a SyncContainer is not possible. "
            "If you require async dependencies create an AsyncContainer via wireup.create_async_container instead. "
            f"List of async factories encountered: {entry}."
        )

        raise WireupError(msg)

    errors: list[Exception] = []

    for gen, _ in reversed(exit_stack):
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

    exit_stack.clear()
    maybe_raise_exc(exc_val=exc_val, exc_tb=exc_tb, container_close_errors=errors)


async def async_clean_exit_stack(
    exit_stack: ExitStack,
    exc_val: BaseException | None = None,
    exc_tb: TracebackType | None = None,
) -> None:
    errors: list[Exception] = []

    for gen, is_async in reversed(exit_stack):
        try:
            if is_async:
                if exc_val:
                    await gen.athrow(exc_val)  # type: ignore[union-attr]
                else:
                    await gen.asend(None)  # type: ignore[union-attr]
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

    exit_stack.clear()
    maybe_raise_exc(exc_val=exc_val, exc_tb=exc_tb, container_close_errors=errors)


def maybe_raise_exc(
    *,
    exc_val: BaseException | None = None,
    exc_tb: TracebackType | None = None,
    container_close_errors: list[Exception] | None = None,
) -> None:
    if not exc_val:
        if container_close_errors:
            raise ContainerCloseError(_CONTAINER_CLOSE_ERR, container_close_errors)
        return

    if exc_tb is not None:
        exc_val.__traceback__ = exc_tb

    if container_close_errors:
        raise ContainerCloseError(_CONTAINER_CLOSE_ERR, container_close_errors)
