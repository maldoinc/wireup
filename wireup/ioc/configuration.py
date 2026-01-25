from __future__ import annotations

import re
from re import Match
from typing import Any, Mapping

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
        # To not break backwards compatibility, we need to check if there exists
        # a value in baggage that matches the full name first
        if name in self.__bag:
            return self.__bag[name]

        match_parts = name.split(".")
        parent = self.__bag

        for i, part in enumerate(match_parts):
            if part == "":
                raise ValueError(
                    f"Provided config key format is invalid: '{name}'."
                    " Please provide a non-empty config-key, or a vaild `dot` separated path, with non-empty parts."
                )
            parent = self.__get_value_from_name_and_holder(i, match_parts, part, parent)

        return parent

    @classmethod
    def __get_value_from_name_and_holder(cls, index: int, matched_parts: list[str], name: str, holder: Any) -> Any:
        if isinstance(holder, Mapping):
            if name not in holder:
                raise UnknownParameterError(name, parent_path=".".join(matched_parts[:index]))

            return holder[name]

        if not hasattr(holder, name):
            raise UnknownParameterError(name, parent_path=".".join(matched_parts[:index]))

        return getattr(holder, name)

    def __interpolate(self, val: str) -> str:
        if val in self.__cache:
            return self.__cache[val]

        def replace_param(match: Match[str]) -> str:
            return str(self.__get_value_from_name(match.group(1)))

        # Accept anything here as we don't impose any rules on dict keys
        res = re.sub(r"\${(.*?)}", replace_param, val, flags=re.DOTALL)
        self.__cache[val] = res

        return res
