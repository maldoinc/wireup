from __future__ import annotations

import re
from re import Match
from typing import Any

from wireup.errors import UnknownParameterError
from wireup.ioc.types import ParameterReference, TemplatedString


class ParameterBag:
    """Parameter flat key-value store for use with a container.

    Allows storing and retrieving of parameters in the bag. Templated strings can be used to interpolate a string
    referencing parameters.

    """

    __slots__ = ("__bag", "__cache")

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        """Initialize an empty ParameterBag.

        ParameterBag holds a flat key-value store of parameter values.
        __bag: A dictionary to store parameter values.
        __cache: A cache for interpolated values.
        """
        self.__bag: dict[str, Any] = {} if values is None else values
        self.__cache: dict[str, str] = {}

    def get(self, param: ParameterReference) -> Any:
        """Get the value of a parameter.

        If the parameter is templated, interpolate it first by replacing placeholders with parameter values.

        :param param: The parameter to retrieve.
        :return: The parameter's value.
        """
        return (
            self.__interpolate(param.value) if isinstance(param, TemplatedString) else self.__get_value_from_name(param)
        )

    def __get_value_from_name(self, name: str) -> Any:
        if name not in self.__bag:
            raise UnknownParameterError(name)

        return self.__bag[name]

    @classmethod
    def __get_value_from_name_and_holder(cls, name: str, holder: Any) -> Any:
        match holder:
            case dict():
                if name not in holder:
                    raise UnknownParameterError(name)

                return holder[name]
            case object():
                if getattr(holder, name, None) is None:
                    raise UnknownParameterError(name)

                return getattr(holder, name)

    def __interpolate(self, val: str) -> str:
        if val in self.__cache:
            return self.__cache[val]

        def replace_param(match: Match[str]) -> str:
            match_parts = match.group(1).split(".")
            parent = self.__get_value_from_name_and_holder(match_parts[0], self.__bag)

            for part in match_parts[1:]:
                parent = self.__get_value_from_name_and_holder(part, parent)

            return str(parent)

        # Accept anything here as we don't impose any rules when adding params
        res = re.sub(r"\${(.*?)}", replace_param, val, flags=re.DOTALL)
        self.__cache[val] = res

        return res
