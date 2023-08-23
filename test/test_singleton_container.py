import unittest

from wireup import Container, container


class TestSingletonContainer(unittest.TestCase):
    def test_singleton_instantiated(self):
        self.assertIsInstance(container, Container)
