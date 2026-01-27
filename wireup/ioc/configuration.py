from __future__ import annotations

import re
from re import Match
from typing import Any

from wireup.errors import UnknownParameterError
from wireup.ioc.types import ConfigurationReference, TemplatedString


class ConfigStore:
    """Config flat key-value store for use with a container.

    Allows storing and retrieving of config. Templated strings can be used to interpolate a string
    referencing other config keys.
    """

    __slots__ = ("__bag", "__cache")

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.__bag: dict[str, Any] = {} if values is None else values
        self.__cache: dict[str, str] = {}

    def get(self, value: ConfigurationReference) -> Any:
        """Get the value of a configuration key or expression."""
        return (
            self.__interpolate(value.value) if isinstance(value, TemplatedString) else self.__get_value_from_name(value)
        )

    def __get_value_from_name(self, name: str) -> Any:
        if name not in self.__bag:
            raise UnknownParameterError(name)

        return self.__bag[name]

    def __interpolate(self, val: str) -> str:
        if val in self.__cache:
            return self.__cache[val]

        def replace_param(match: Match[str]) -> str:
            return str(self.__get_value_from_name(match.group(1)))

        # Accept anything here as we don't impose any rules on dict keys
        res = re.sub(r"\${(.*?)}", replace_param, val, flags=re.DOTALL)
        self.__cache[val] = res

        return res
