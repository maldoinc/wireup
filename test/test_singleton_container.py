import unittest

from wireup import container, Container


class TestSingletonContainer(unittest.TestCase):
    def test_singleton_instantiated(self):
        self.assertIsInstance(container, Container)
