from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from wireup.errors import ContainerCloseError, WireupError

if TYPE_CHECKING:
    from types import AsyncGeneratorType, GeneratorType


def clean_exit_stack(exit_stack: list[GeneratorType[Any, Any, Any] | AsyncGeneratorType[Any, Any]]) -> None:
    errors: list[Exception] = []

    if any(inspect.isasyncgen(gen) for gen in exit_stack):
        msg = "Async generators need to be closed with container.aclose()"
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
