from __future__ import annotations

import contextlib
from typing import Iterator

from typing_extensions import Self


class Codegen:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent_level = 0

    def append(self, code: str) -> None:
        indentation = "    " * self._indent_level
        self._lines.append(f"{indentation}{code}")

    def __iadd__(self, code: str) -> Self:
        self.append(code)
        return self

    @contextlib.contextmanager
    def indent(self) -> Iterator[None]:
        self._indent_level += 1
        try:
            yield
        finally:
            self._indent_level -= 1

    def get_source(self) -> str:
        return "\n".join(self._lines) + "\n"
