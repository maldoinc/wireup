import unittest

import wireup

from test.unit.services import with_annotations
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService
from test.unit.services.with_annotations import services
from test.unit.services.with_annotations.env import EnvService
from test.unit.services.with_annotations.services import IFoo


class ModuleLoadingTest(unittest.TestCase):
    def test_warmup_loads_all_in_module_with_annotations(self):
        container = wireup.create_sync_container(service_modules=[with_annotations], parameters={"env_name": "dev"})

        self.assertEqual("dev", container.get(EnvService).env_name)
        self.assertEqual("foo", container.get(IFoo).get_foo())
        self.assertEqual(5, container.get(TrulyRandomService, qualifier="foo").get_truly_random())
        self.assertEqual(4, container.get(RandomService, qualifier="foo").get_random())

    def test_loads_module_is_file(self):
        # Assert that loading works when the module is a file instead of the entire module
        container = wireup.create_sync_container(parameters={"env_name": "dev"}, service_modules=[services])

        self.assertEqual("foo", container.get(services.IFoo).get_foo())
        self.assertEqual(4, container.get(RandomService, qualifier="foo").get_random())
        self.assertEqual(5, container.get(TrulyRandomService, qualifier="foo").get_truly_random())
