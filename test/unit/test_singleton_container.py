import unittest

from wireup import DependencyContainer, container


class TestSingletonContainer(unittest.TestCase):
    def test_singleton_instantiated(self):
        self.assertIsInstance(container, DependencyContainer)
