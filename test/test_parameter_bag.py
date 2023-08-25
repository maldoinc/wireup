import unittest

from wireup.ioc.parameter import ParameterBag, TemplatedString


class TestParameterBag(unittest.TestCase):
    def setUp(self):
        self.parameter_bag = ParameterBag()

    def test_get_parameter(self):
        self.parameter_bag.put("name", "test")

        self.assertEqual(self.parameter_bag.get("name"), "test")

    def test_resolve_interpolated_via_value(self):
        self.parameter_bag.put("product_ver", "0.0.1")
        beta_ver = self.parameter_bag.get(TemplatedString("v${product_ver}-beta"))

        self.assertEqual(beta_ver, "v0.0.1-beta")

    def test_resolve_interpolated_via_class(self):
        self.parameter_bag.put("product_ver", "0.0.1")
        rc = self.parameter_bag.get(TemplatedString("v${product_ver}-rc1"))

        self.assertEqual(rc, "v0.0.1-rc1")

    def test_param_does_not_exist_raises(self):
        self.parameter_bag.put("foo", "bar")

        self.assertRaises(ValueError, lambda: self.parameter_bag.get("does_not_exist"))
        self.assertRaises(
            ValueError,
            lambda: self.parameter_bag.get(TemplatedString("${foo}-${does_not_exist}")),
        )
