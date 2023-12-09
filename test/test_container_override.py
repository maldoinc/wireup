import unittest
from unittest.mock import MagicMock

from test.services.no_annotations.random.random_service import RandomService
from wireup import DependencyContainer, ParameterBag


class TestContainerOverride(unittest.TestCase):
    def setUp(self) -> None:
        self.container = DependencyContainer(ParameterBag())

    def test_container_overrides_deps_service_locator(self):
        self.container.register(RandomService)

        random_mock = MagicMock()
        random_mock.get_random.return_value = 5
        self.assertEqual(random_mock.get_random(), 5)

        with self.container.override(target=RandomService, new=random_mock):
            svc = self.container.get(RandomService)

            self.assertEqual(svc.get_random(), 5)
