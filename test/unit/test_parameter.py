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
