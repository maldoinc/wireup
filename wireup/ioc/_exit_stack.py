from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup.errors import ContainerCloseError

if TYPE_CHECKING:
    from types import GeneratorType


def clean_exit_stack(exit_stack: list[GeneratorType[Any, Any, Any]]) -> None:
    errors: list[Exception] = []

    while exit_stack and (gen := exit_stack.pop()):
        try:
            gen.send(None)
        except StopIteration:  # noqa: PERF203
            pass
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    if errors:
        raise ContainerCloseError(errors)
