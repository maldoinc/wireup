from __future__ import annotations

import re
from collections import defaultdict
from re import Match
from typing import Any

from .types import ParameterReference, TemplatedString


class ParameterBag:
    """Parameter flat key-value store for use with a container.

    Allows storing and retrieving of parameters in the bag. Templated strings can be used to interpolate a string
    referencing parameters.

    """

    __slots__ = ("__bag", "__cache", "__param_cache")

    def __init__(self) -> None:
        """Initialize an empty ParameterBag.

        ParameterBag holds a flat key-value store of parameter values.
        __bag: A dictionary to store parameter values.
        __cache: A cache for interpolated values.
        __param_cache: A dictionary to keep track of which cache entries involve each parameter.
        """
        self.__bag: dict[str, Any] = {}
        self.__cache: dict[str, str] = {}
        # __param_cache is used to invalidate cache entries related to specific parameters.
        # It maps parameter names to the set of cache entry keys that involve that parameter.
        self.__param_cache: dict[str, set[str]] = defaultdict(set)

    def put(self, name: str, val: Any) -> None:
        """Put a parameter value into the bag. This overwrites any previous values.

        :param name: The name of the parameter.
        :param val: The value of the parameter.
        """
        self.__bag[name] = val
        # Clear cache entries involving this parameter name
        self.__clear_cache_for_name(name)

    def get_all(self) -> dict[str, Any]:
        """Get all parameters stored in the bag.

        :return: A dictionary containing all parameter names and their values.
        """
        return self.__bag

    def get(self, param: ParameterReference) -> Any:
        """Get the value of a parameter.

        If the parameter is templated, interpolate it first by replacing placeholders with parameter values.

        :param param: The parameter to retrieve.
        :return: The parameter's value.
        """
        return (
            self.__interpolate(param.value) if isinstance(param, TemplatedString) else self.__get_value_from_name(param)
        )

    def update(self, new_params: dict[str, Any]) -> None:
        """Update the bag with new set of parameters.

        Parameters from new_params will overwrite any existing parameters set with the same name.

        :param new_params: A dictionary of parameter names and their updated values.
        """
        for name, value in new_params.items():
            self.put(name, value)

    def __get_value_from_name(self, name: str) -> Any:
        if name not in self.__bag:
            msg = f"Unknown parameter {name} requested"
            raise ValueError(msg)

        return self.__bag[name]

    def __interpolate(self, val: str) -> str:
        if val in self.__cache:
            return self.__cache[val]

        def replace_param(match: Match[str]) -> str:
            param_name = match.group(1)
            param_value = str(self.__get_value_from_name(param_name))

            # Populate __param_cache with the parameter name involved in this cache entry
            self.__param_cache[param_name].add(val)

            return param_value

        # Let's accept anything here as we don't impose any rules when adding params
        res = re.sub(r"\${(.*?)}", replace_param, val, flags=re.DOTALL)
        self.__cache[val] = res

        return res

    def __clear_cache_for_name(self, name: str) -> None:
        """Clear cache entries that involve the specified parameter name."""
        for key in self.__param_cache[name]:
            del self.__cache[key]

        del self.__param_cache[name]
