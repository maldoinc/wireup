import unittest

from wireup.errors import UnknownParameterError
from wireup.ioc.parameter import ParameterBag, TemplatedString
from wireup.ioc.types import ParameterWrapper


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
        with self.assertRaises(UnknownParameterError):
            self.bag.get("unknown_param")

    def test_update_assert_merges(self):
        self.bag.put("param1", 42)
        self.bag.put("param2", "foo")
        self.bag.update({"param2": "value"})

        self.assertEqual(self.bag.get("param1"), 42)
        self.assertEqual(self.bag.get("param2"), "value")

    def test_interpolate_unknown_parameter(self):
        templated_str = TemplatedString("Test ${unknown_param}")

        with self.assertRaises(UnknownParameterError):
            self.bag.get(templated_str)

    def test_all(self):
        self.bag.put("foo", "bar")
        self.bag.update({"bar": "baz", "baz": "qux"})

        self.assertEqual(self.bag.get_all(), {"foo": "bar", "bar": "baz", "baz": "qux"})

    def test_parameter_interpolation_is_cached(self):
        self.bag.put("foo", "bar")
        self.assertEqual(self.bag.get(TemplatedString("${foo}-${foo}")), "bar-bar")
        self.assertEqual(self.bag.get(TemplatedString("${foo}-${foo}")), "bar-bar")
        self.assertEqual(self.bag._ParameterBag__cache, {"${foo}-${foo}": "bar-bar"})

    def test_get_parameter_unknown(self):
        with self.assertRaises(UnknownParameterError) as context:
            self.bag.get("name")

        self.assertEqual("Unknown parameter requested: name", str(context.exception))

    def test_get_parameter_interpolation_unknown(self):
        with self.assertRaises(UnknownParameterError) as context:
            self.bag.get(TemplatedString("name/${dummy}"))

        self.assertEqual("Unknown parameter requested: dummy", str(context.exception))

    def test_get_interpolated_result_is_cached(self):
        self.bag.put("name", "Bob")
        self.assertEqual(self.bag.get(TemplatedString("Hi ${name}")), "Hi Bob")
        self.assertEqual({"Hi ${name}": "Hi Bob"}, self.bag._ParameterBag__cache)

    def test_interpolated_cache_entries_cleared(self):
        self.bag.put("name", "Bob")
        self.bag.put("env", "test")

        self.assertEqual(self.bag.get(TemplatedString("Hi ${name}")), "Hi Bob")
        self.assertEqual(self.bag.get(TemplatedString("Hi from ${env}")), "Hi from test")
        self.assertEqual({"Hi ${name}": "Hi Bob", "Hi from ${env}": "Hi from test"}, self.bag._ParameterBag__cache)

        self.bag.put("env", "prod")
        self.assertEqual({"Hi ${name}": "Hi Bob"}, self.bag._ParameterBag__cache)  # Check that entry was removed.

        self.assertEqual(self.bag.get(TemplatedString("Hi from ${env}")), "Hi from prod")
        self.assertEqual({"Hi ${name}": "Hi Bob", "Hi from ${env}": "Hi from prod"}, self.bag._ParameterBag__cache)


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
