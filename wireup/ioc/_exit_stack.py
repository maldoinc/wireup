from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from wireup.errors import ContainerCloseError, WireupError

if TYPE_CHECKING:
    from types import AsyncGeneratorType, GeneratorType


def clean_exit_stack(exit_stack: list[GeneratorType[Any, Any, Any] | AsyncGeneratorType[Any, Any]]) -> None:
    errors: list[Exception] = []

    if async_gen := [gen for gen in exit_stack if inspect.isasyncgen(gen)]:
        msg = (
            "The following generators are async factories and closing the container with `container.close()`"
            f" is not possible. Replace the `container.close()` call with `await container.aclose()`. "
            f"If you used `wireup.enter_scope`, you should use `wireup.enter_async_scope` instead. "
            f"List of async factories: {async_gen}."
        )
        raise WireupError(msg)

    while exit_stack and (gen := exit_stack.pop()):
        try:
            gen.send(None)  # type: ignore[union-attr]
        except StopIteration:  # noqa: PERF203
            pass
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    if errors:
        raise ContainerCloseError(errors)


async def async_clean_exit_stack(exit_stack: list[GeneratorType[Any, Any, Any] | AsyncGeneratorType[Any, Any]]) -> None:
    errors: list[Exception] = []

    while exit_stack and (gen := exit_stack.pop()):
        try:
            if inspect.isasyncgen(gen):
                await gen.asend(None)
            else:
                gen.send(None)

        except StopIteration:  # noqa: PERF203
            pass
        except StopAsyncIteration:
            pass
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    if errors:
        raise ContainerCloseError(errors)
