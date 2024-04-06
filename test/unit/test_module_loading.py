import unittest
from test.unit.services import no_annotations, with_annotations
from test.unit.services.with_annotations.env import EnvService

import wireup
from wireup import DependencyContainer, ParameterBag, register_all_in_module, warmup_container


class ModuleLoadingTest(unittest.TestCase):
    def test_register_all_in_module_is_recursive(self):
        container = DependencyContainer(ParameterBag())
        register_all_in_module(container, module=no_annotations, pattern="*Service")

        registered = {t.__name__ for t in container.context.dependencies}
        self.assertEqual(
            registered, {"BarService", "DbService", "TrulyRandomService", "BazService", "FooService", "RandomService"}
        )

    def test_warmup_loads_all_in_module_with_annotations(self):
        wireup.container.params.put("env_name", "dev")
        warmup_container(wireup.container, service_modules=[with_annotations])

        self.assertEqual("dev", wireup.container.get(EnvService).env_name)
