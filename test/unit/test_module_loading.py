import unittest
from test.unit.services import no_annotations, with_annotations
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService
from test.unit.services.with_annotations import services
from test.unit.services.with_annotations.env import EnvService
from test.unit.services.with_annotations.services import IFoo

import wireup
from wireup import DependencyContainer, ParameterBag, initialize_container, register_all_in_module, warmup_container


class ModuleLoadingTest(unittest.TestCase):
    def test_register_all_in_module_is_recursive(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=no_annotations, pattern="*Service")

        registered = {t.__name__ for t in container.context.dependencies}
        self.assertEqual(
            registered, {"BarService", "DbService", "TrulyRandomService", "BazService", "FooService", "RandomService"}
        )

    def test_warmup_loads_all_in_module_with_annotations(self):
        container = DependencyContainer(ParameterBag())
        container.params.put("env_name", "dev")
        warmup_container(container, service_modules=[with_annotations])

        self.assertEqual("dev", container.get(EnvService).env_name)
        self.assertEqual("foo", container.get(IFoo).get_foo())
        self.assertEqual(5, container.get(TrulyRandomService, qualifier="foo").get_truly_random())
        self.assertEqual(4, container.get(RandomService, qualifier="foo").get_random())

    def test_loads_module_is_file(self):
        # Assert that loading works when the module is a file instead of the entire module
        container = DependencyContainer(ParameterBag())
        container.params.put("env_name", "dev")
        initialize_container(container, service_modules=[services])

        self.assertEqual("foo", container.get(services.IFoo).get_foo())
        self.assertEqual(4, container.get(RandomService, qualifier="foo").get_random())
        self.assertEqual(5, container.get(TrulyRandomService, qualifier="foo").get_truly_random())

    def test_initialize_is_idempotent_recreates_container(self):
        id_start = id(wireup.container)
        initialize_container(service_modules=[services])
        id1 = id(wireup.container)
        initialize_container(service_modules=[services])
        id2 = id(wireup.container)

        self.assertNotEqual(id_start, id1)
        self.assertNotEqual(id1, id2)
