import wireup

from test.unit.services import with_annotations
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService
from test.unit.services.with_annotations import services
from test.unit.services.with_annotations.env import EnvService
from test.unit.services.with_annotations.services import Foo


def test_warmup_loads_all_in_module_with_annotations() -> None:
    container = wireup.create_sync_container(injectables=[with_annotations], config={"env_name": "dev"})

    assert container.get(EnvService).env_name == "dev"
    assert container.get(Foo).get_foo() == "foo"
    assert container.get(TrulyRandomService, qualifier="foo").get_truly_random() == 5
    assert container.get(RandomService, qualifier="foo").get_random() == 4


def test_loads_module_is_file() -> None:
    # Assert that loading works when the module is a file instead of the entire module
    container = wireup.create_sync_container(config={"env_name": "dev"}, injectables=[services])

    assert container.get(services.Foo).get_foo() == "foo"
    assert container.get(RandomService, qualifier="foo").get_random() == 4
    assert container.get(TrulyRandomService, qualifier="foo").get_truly_random() == 5
