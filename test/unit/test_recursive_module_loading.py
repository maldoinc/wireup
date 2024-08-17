import re
import unittest

from wireup import DependencyContainer, ParameterBag, register_all_in_module

from test.unit import services


class RecursiveModuleLoadingTest(unittest.TestCase):
    def test_register_all_in_module_is_recursive(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=services, pattern="*Service")
        self.assertSetEqual(
            {x.__name__ for x in container.context.dependencies},
            {
                "EnvService",
                "TrulyRandomService",
                "RandomService",
                "DbService",
                "BarService",
                "BazService",
                "FooService",
            },
        )

    def test_register_all_in_module_is_recursive_multiple_patterns(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=services, pattern=re.compile("^Db.+|.+Repository$"))
        self.assertSetEqual(
            {x.__name__ for x in container.context.dependencies},
            {"DbService", "FooRepository"},
        )

    def test_register_all_in_module_is_recursive_matches_pattern(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=services, pattern="*Random*")
        self.assertEqual(
            {x.__name__ for x in container.context.dependencies},
            {
                "RandomService",
                "TrulyRandomService",
            },
        )
