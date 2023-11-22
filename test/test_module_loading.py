import unittest
from test import services
from test.services.with_annotations.env.env_service import EnvService

import wireup
from wireup import DependencyContainer, ParameterBag, register_all_in_module, warmup_container


class ModuleLoadingTest(unittest.TestCase):
    def test_register_all_in_module_is_recursive(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=services.no_annotations)

        registered = {t.__name__ for t in container.context.dependencies.keys()}
        self.assertEqual(
            registered, {"BarService", "DbService", "TrulyRandomService", "BazService", "FooService", "RandomService"}
        )

    def test_warmup_loads_all_in_module_with_annotations(self):
        wireup.container.params.put("env_name", "dev")
        warmup_container(wireup.container, service_modules=[services.with_annotations])

        self.assertEqual("dev", wireup.container.get(EnvService).env_name)
