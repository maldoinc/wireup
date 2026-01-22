import re

import pytest
from wireup.errors import UnknownParameterError
from wireup.ioc.configuration import ConfigStore
from wireup.ioc.types import TemplatedString


def test_parameter_bag_initialization():
    bag = ConfigStore()
    assert isinstance(bag, ConfigStore)


def test_parameter_bag_initialization_with_values():
    values = {"param1": "value1", "param2": "value2"}
    bag = ConfigStore(values)
    assert bag.get("param1") == "value1"
    assert bag.get("param2") == "value2"


def test_get_existing_parameter():
    values = {"param1": "value1"}
    bag = ConfigStore(values)
    assert bag.get("param1") == "value1"


def test_get_non_existing_parameter():
    bag = ConfigStore()
    with pytest.raises(UnknownParameterError):
        bag.get("non_existing_param")


def test_get_templated_string():
    values = {"param1": "value1", "param2": "value2"}
    bag = ConfigStore(values)
    templated_string = TemplatedString("${param1} and ${param2}")
    assert bag.get(templated_string) == "value1 and value2"


def test_get_templated_string_with_dot_notation():
    values = {
        "param1": {
            "nested1": "value1",
        },
        "param2": {
            "nested2": None,
        },
    }
    bag = ConfigStore(values)
    templated_string = TemplatedString("${param1.nested1} and ${param2.nested2}")
    assert bag.get(templated_string) == "value1 and None"


def test_get_templated_string_with_dot_notation_gives_priority_to_existing_keys_containing_dots():
    values = {"foo.bar": 1, "foo": {"bar": 2}}
    bag = ConfigStore(values)
    templated_string = TemplatedString("${foo.bar}")
    assert bag.get(templated_string) == "1"


def test_get_templated_string_with_dot_notation_without_parameter_expression():
    values = {
        "param1": {
            "nested1": "value1",
        },
        "param2": {
            "nested2": None,
        },
    }
    bag = ConfigStore(values)
    with pytest.raises(UnknownParameterError, match=re.escape("Unknown config key requested: param1.nested1")):
        bag.get("param1.nested1")


def test_get_templated_string_with_dot_notation_with_non_existing_param():
    values = {
        "param1": {
            "nested1": {
                "nested1_1": "value1",
            },
        }
    }
    bag = ConfigStore(values)

    templated_string = TemplatedString("${param2.nested2.nested1_1}")
    with pytest.raises(
        UnknownParameterError,
        match=re.escape("Unknown config key requested: param2"),
    ):
        bag.get(templated_string)

    templated_string = TemplatedString("${param1.nested2.nested1_1}")
    with pytest.raises(
        UnknownParameterError,
        match=re.escape("Unknown config key requested: param1.nested2. 'nested2' not found in 'param1'"),
    ):
        bag.get(templated_string)

    templated_string = TemplatedString("${param1.nested1.nested1_2}")
    with pytest.raises(
        UnknownParameterError,
        match=re.escape(
            "Unknown config key requested: param1.nested1.nested1_2. 'nested1_2' not found in 'param1.nested1'"
        ),
    ):
        bag.get(templated_string)


def test_get_templated_string_with_dot_notation__param_is_object():
    class TestObject:
        def __init__(self) -> None:
            self.property1 = "value1"

        @property
        def property2(self) -> str:
            return "value2"

    values = {"param1": TestObject()}
    bag = ConfigStore(values)
    templated_string = TemplatedString("${param1.property1}")
    assert bag.get(templated_string) == "value1"

    templated_string = TemplatedString("${param1.property2}")
    assert bag.get(templated_string) == "value2"

    templated_string = TemplatedString("${param1.property3}")
    with pytest.raises(UnknownParameterError):
        bag.get(templated_string)


def test_get_templated_string_with_broken_paths():
    values = {"param1": {"property1": "value1"}}
    bag = ConfigStore(values)

    templated_string = TemplatedString("${param1..property1}")
    with pytest.raises(
        UnknownParameterError, match=re.escape("Unknown config key requested: param1.. '' not found in 'param1'")
    ):
        bag.get(templated_string)

    templated_string = TemplatedString("${param1.}")
    with pytest.raises(
        UnknownParameterError, match=re.escape("Unknown config key requested: param1.. '' not found in 'param1'")
    ):
        bag.get(templated_string)

    templated_string = TemplatedString("${.param1}")
    with pytest.raises(UnknownParameterError, match=re.escape("Unknown config key requested: ")):
        bag.get(templated_string)

    templated_string = TemplatedString("${.param1.}")
    with pytest.raises(UnknownParameterError, match=re.escape("Unknown config key requested: ")):
        bag.get(templated_string)


def test_get_templated_string_with_non_existing_param():
    values = {"param1": "value1"}
    bag = ConfigStore(values)
    templated_string = TemplatedString("${param1} and ${param2}")
    with pytest.raises(UnknownParameterError):
        bag.get(templated_string)


def test_cache_interpolated_values():
    values = {"param1": "value1"}
    bag = ConfigStore(values)
    templated_string = TemplatedString("${param1}")
    assert bag.get(templated_string) == "value1"
    assert templated_string.value in bag._ConfigStore__cache  # type: ignore[reportAttributeAccessIssue]
    assert bag._ConfigStore__cache[templated_string.value] == "value1"  # type: ignore[reportAttributeAccessIssue]
