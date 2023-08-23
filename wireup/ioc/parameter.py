import functools
import re
from typing import Dict, Any

from .container_util import ParameterReference, TemplatedString


class ParameterBag:
    def __init__(self) -> None:
        """
        Initialize an empty ParameterBag.

        The ParameterBag holds a flat key-value store of parameter values.
        """
        self.__bag: Dict[str, Any] = {}

    def put(self, name: str, val: Any) -> None:
        """
        Put a parameter value into the bag. This overwrites any previous values.

        :param name: The name of the parameter.
        :param val: The value of the parameter.
        """
        self.__bag[name] = val

    def all(self) -> Dict[str, Any]:
        """
        Get all parameters stored in the bag.

        :return: A dictionary containing all parameter names and their values.
        """
        return self.__bag

    def get(self, param: ParameterReference) -> Any:
        """
        Get the value of a parameter.
        If the parameter is templated, interpolate it first by replacing placeholders with parameter values.

        :param param: The parameter to retrieve.
        :return: The parameter's value.
        """
        return (
            self.__interpolate(param.value) if isinstance(param, TemplatedString) else self.__get_value_from_name(param)
        )

    def update(self, new_params: Dict[str, Any]) -> None:
        """
        Update the bag with new set of parameters.
        Parameters from new_params will overwrite any existing parameters set with the same name.

        :param new_params: A dictionary of parameter names and their updated values.
        """
        self.__bag.update(new_params)

    # Private methods...

    def __get_value_from_name(self, name: str) -> Any:
        if name not in self.__bag:
            raise ValueError(f"Unknown parameter {name} requested")

        return self.__bag[name]

    @functools.lru_cache(maxsize=256)
    def __interpolate(self, val) -> str:
        return re.sub(
            r"\${(.*?)}",  # Let's accept anything here as we don't impose any rules when adding params
            # Since we're concatenating strings we need to convert any parameters we get to str
            lambda match: str(self.__get_value_from_name(match.group(1))),
            val,
            flags=re.DOTALL,
        )
