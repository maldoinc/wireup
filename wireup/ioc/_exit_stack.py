from __future__ import annotations

import inspect
from typing import Any, AsyncGenerator, Generator

from wireup.errors import ContainerCloseError, WireupError


def clean_exit_stack(exit_stack: list[Generator[Any, Any, Any] | AsyncGenerator[Any, Any]]) -> None:
    if not exit_stack:
        return

    errors: list[Exception] = []

    if async_gen := [gen for gen in exit_stack if inspect.isasyncgen(gen)]:
        msg = (
            "The following generators are async factories and closing them with a SyncContainer is not possible. "
            "If you require async dependencies create an AsyncContainer via wireup.create_async_container instead. "
            f"List of async factories encountered: {async_gen}."
        )

        raise WireupError(msg)

    for gen in reversed(exit_stack):
        try:
            gen.send(None)  # type: ignore[union-attr]
        except StopIteration:  # noqa: PERF203
            pass
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    if errors:
        raise ContainerCloseError(errors)


async def async_clean_exit_stack(exit_stack: list[Generator[Any, Any, Any] | AsyncGenerator[Any, Any]]) -> None:
    if not exit_stack:
        return

    errors: list[Exception] = []

    for gen in reversed(exit_stack):
        try:
            if inspect.isasyncgen(gen):
                await gen.asend(None)
            else:
                gen.send(None)  # type: ignore[union-attr]

        except StopIteration:  # noqa: PERF203
            pass
        except StopAsyncIteration:
            pass
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    if errors:
        raise ContainerCloseError(errors)
