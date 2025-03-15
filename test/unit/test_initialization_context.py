import pytest
from wireup import Inject
from wireup.ioc.initialization_context import InitializationContext
from wireup.ioc.types import AnnotatedParameter

from test.unit.services.no_annotations.random.random_service import RandomService


@pytest.fixture
def context() -> InitializationContext:
    return InitializationContext()


def test_init_target(context: InitializationContext):
    assert context.init_target(RandomService)
    assert RandomService in context.dependencies
    assert context.dependencies[RandomService] == {}


def test_init_target_with_lifetime(context: InitializationContext):
    assert context.init_target(RandomService, "singleton")
    assert RandomService in context.lifetime
    assert context.lifetime[RandomService] == "singleton"


def test_init_target_existing(context: InitializationContext):
    context.init_target(RandomService)
    assert not context.init_target(RandomService)


def test_add_dependency(context: InitializationContext):
    context.init_target(RandomService)
    param = AnnotatedParameter(klass=int)
    context.add_dependency(RandomService, "param", param)
    assert context.dependencies[RandomService]["param"] == param


def test_remove_dependencies(context: InitializationContext):
    context.init_target(RandomService)
    param1 = AnnotatedParameter(klass=int, annotation=Inject(param="foo"))
    param2 = AnnotatedParameter(klass=str, annotation=Inject(param="bar"))
    context.add_dependency(RandomService, "param1", param1)
    context.add_dependency(RandomService, "param2", param2)
    context.remove_dependencies(RandomService, {"param1"})
    assert "param1" not in context.dependencies[RandomService]
    assert "param2" in context.dependencies[RandomService]
