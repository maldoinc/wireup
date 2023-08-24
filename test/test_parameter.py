import unittest

from wireup.ioc.container_util import ParameterWrapper
from wireup.ioc.parameter import ParameterBag, TemplatedString


class TestTemplatedString(unittest.TestCase):
    def test_init(self):
        val = "test value"
        templated_str = TemplatedString(val)
        self.assertEqual(templated_str.value, val)


class TestParameterBag(unittest.TestCase):
    def test_put_get(self):
        param_bag = ParameterBag()
        param_bag.put("param1", 42)

        self.assertEqual(param_bag.get("param1"), 42)

    def test_put_get_templated_string_is_converted(self):
        param_bag = ParameterBag()
        param_bag.put("param1", 42)
        templated_str = TemplatedString("Number: ${param1}")

        self.assertEqual(param_bag.get(templated_str), "Number: 42")
        self.assertEqual(param_bag.get(TemplatedString("${param1}")), "42")

    def test_get_unknown_parameter(self):
        param_bag = ParameterBag()

        with self.assertRaises(ValueError):
            param_bag.get("unknown_param")

    def test_update(self):
        param_bag = ParameterBag()
        param_bag.put("param1", 42)
        param_bag.update({"param2": "value"})

        self.assertEqual(param_bag.get("param2"), "value")

    def test_interpolate(self):
        param_bag = ParameterBag()
        param_bag.put("param1", "value")
        templated_str = TemplatedString("Test ${param1}")

        self.assertEqual(param_bag.get(templated_str), "Test value")

    def test_interpolate_unknown_parameter(self):
        param_bag = ParameterBag()
        templated_str = TemplatedString("Test ${unknown_param}")

        with self.assertRaises(ValueError):
            param_bag.get(templated_str)

    def test_all(self):
        bag = ParameterBag()
        bag.put("foo", "bar")
        bag.update({"bar": "baz", "baz": "qux"})

        self.assertEqual(bag.get_all(), {"foo": "bar", "bar": "baz", "baz": "qux"})


class TestParameterPlaceholder(unittest.TestCase):
    def test_init(self):
        param_ref = "param"
        placeholder = ParameterWrapper(param_ref)

        self.assertEqual(placeholder.param, param_ref)
