import unittest

from test import services
from wireup import DependencyContainer, ParameterBag, register_all_in_module


class RecursiveModuleLoadingTest(unittest.TestCase):
    def test_register_all_in_module_is_recursive(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=services)
        self.assertEqual(
            [x.__name__ for x in container.context.dependencies.keys()],
            [
                "EnvService",
                "TrulyRandomService",
                "RandomService",
                "DbService",
                "BarService",
                "BazService",
                "FooService",
            ],
        )

    def test_register_all_in_module_is_recursive_matches_pattern(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=services, pattern="*Random*")
        self.assertEqual(
            [x.__name__ for x in container.context.dependencies.keys()],
            [
                "TrulyRandomService",
                "RandomService",
            ],
        )
