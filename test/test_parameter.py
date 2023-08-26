import unittest

from wireup.ioc.container_util import ParameterWrapper, ParameterReference
from wireup.ioc.parameter import ParameterBag, TemplatedString


class TestParameterBag(unittest.TestCase):
    def setUp(self) -> None:
        self.bag = ParameterBag()

    def test_put_get(self):
        self.bag.put("param1", 42)

        self.assertEqual(self.bag.get("param1"), 42)

    def test_put_get_templated_string_is_converted(self):
        self.bag.put("param1", 42)
        templated_str = TemplatedString("Number: ${param1}")

        self.assertEqual(self.bag.get(templated_str), "Number: 42")
        self.assertEqual(self.bag.get(TemplatedString("${param1}")), "42")

    def test_get_unknown_parameter(self):
        with self.assertRaises(ValueError):
            self.bag.get("unknown_param")

    def test_update_assert_merges(self):
        self.bag.put("param1", 42)
        self.bag.put("param2", "foo")
        self.bag.update({"param2": "value"})

        self.assertEqual(self.bag.get("param1"), 42)
        self.assertEqual(self.bag.get("param2"), "value")

    def test_interpolate_unknown_parameter(self):
        templated_str = TemplatedString("Test ${unknown_param}")

        with self.assertRaises(ValueError):
            self.bag.get(templated_str)

    def test_all(self):
        self.bag.put("foo", "bar")
        self.bag.update({"bar": "baz", "baz": "qux"})

        self.assertEqual(self.bag.get_all(), {"foo": "bar", "bar": "baz", "baz": "qux"})

    def test_parameter_interpolation_is_cached(self):
        self.bag.put("foo", "bar")
        self.assertEqual(self.bag.get(TemplatedString("${foo}-${foo}")), "bar-bar")
        self.assertEqual(self.bag.get(TemplatedString("${foo}-${foo}")), "bar-bar")
        self.assertEqual(self.bag._ParameterBag__cache, {"${foo}-${foo}": "bar-bar"})  # noqa: SLF001


class TestParameterPlaceholder(unittest.TestCase):
    def test_init(self):
        param_ref = "param"
        placeholder = ParameterWrapper(param_ref)

        self.assertEqual(placeholder.param, param_ref)


class TestTemplatedString(unittest.TestCase):
    def test_init(self):
        val = "test value"
        templated_str = TemplatedString(val)
        self.assertEqual(templated_str.value, val)
