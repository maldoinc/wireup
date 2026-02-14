import re
import unittest
from typing import Protocol
from unittest.mock import MagicMock

import pytest
import wireup
from typing_extensions import Annotated
from wireup import Inject, abstract, create_async_container, create_sync_container, inject_from_container, injectable
from wireup._annotations import Injected
from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.factory_compiler import FactoryCompiler
from wireup.ioc.types import InjectableOverride

from test.conftest import Container
from test.unit.services.abstract_multiple_bases import FooBar
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.services import (
    Foo,
    FooImpl,
    ScopedService,
    TransientService,
    random_service_factory,
)
from test.unit.util import run


def test_container_overrides_deps_service_locator(container: Container):
    container = wireup.create_sync_container(injectables=[random_service_factory])

    random_mock = MagicMock()
    random_mock.get_random.return_value = 5

    @wireup.inject_from_container(container)
    def get_random_via_inject(svc: Annotated[RandomService, Inject(qualifier="foo")]) -> int:
        return svc.get_random()

    with container.override.injectable(target=RandomService, qualifier="foo", new=random_mock):
        svc = container.get(RandomService, qualifier="foo")
        assert svc.get_random() == 5
        assert get_random_via_inject() == 5

    random_mock.get_random.assert_called()
    assert container.get(RandomService, qualifier="foo").get_random() == 4
    assert get_random_via_inject() == 4


async def test_container_overrides_deps_service_locator_interface():
    container = wireup.create_sync_container(injectables=[Foo, FooImpl])

    foo_mock = MagicMock()
    foo_mock.get_foo.return_value = "mock"

    @wireup.inject_from_container(container)
    def get_foo_via_inject(svc: Injected[Foo]) -> str:
        return svc.get_foo()

    with container.override.injectable(target=Foo, new=foo_mock):
        svc = await run(container.get(Foo))
        assert svc.get_foo() == "mock"
        assert get_foo_via_inject() == "mock"

    res = await run(container.get(Foo))
    assert res.get_foo() == "foo"
    assert get_foo_via_inject() == "foo"


async def test_container_override_many_with_qualifier(container: Container):
    rand1_mock = MagicMock()
    rand2_mock = MagicMock()

    overrides = [
        InjectableOverride(target=ScopedService, new=rand1_mock),
        InjectableOverride(target=TransientService, new=rand2_mock),
    ]

    @wireup.inject_from_container(container)
    def target(scoped: Injected[ScopedService], transient: Injected[TransientService]) -> None:
        assert scoped is rand1_mock
        assert transient is rand2_mock

    with container.override.injectables(overrides=overrides):
        target()


async def test_raises_on_unknown_override(container: Container):
    with pytest.raises(
        UnknownOverrideRequestedError,
        match=re.escape("Cannot override unknown Type unittest.case.TestCase with qualifier 'foo'."),
    ):
        with container.override.injectable(target=unittest.TestCase, qualifier="foo", new=MagicMock()):
            pass


async def test_overrides_async_dependency() -> None:
    @wireup.injectable
    async def async_foo_factory() -> FooBar:
        return FooBar()

    container = wireup.create_async_container(injectables=[async_foo_factory])

    @wireup.inject_from_container(container)
    async def get_foobar_via_inject(svc: Injected[FooBar]) -> str:
        return svc.foo

    foo_mock = MagicMock()
    foo_mock.foo = "mock"

    with container.override.injectable(target=FooBar, new=foo_mock):
        svc = await container.get(FooBar)
        assert svc.foo == "mock"
        assert await get_foobar_via_inject() == "mock"

    res = await container.get(FooBar)
    assert res.foo == "bar"
    assert await get_foobar_via_inject() == "bar"


async def test_override_async_transitive_dependency_with_sync_instance():
    class FooDep:
        pass

    @wireup.injectable
    async def async_foo_dep() -> FooDep:
        return FooDep()

    @wireup.injectable
    class BarDep:
        def __init__(self, foo: FooDep):
            self.foo = foo

    class FooOverride:
        pass

    container = wireup.create_async_container(injectables=[async_foo_dep, BarDep])

    @wireup.inject_from_container(container)
    async def get_bar_via_inject(bar: Injected[BarDep]) -> BarDep:
        return bar

    with container.override.injectable(FooDep, FooOverride()):
        bar = await container.get(BarDep)
        assert isinstance(bar.foo, FooOverride)
        bar_via_inject = await get_bar_via_inject()
        assert isinstance(bar_via_inject.foo, FooOverride)


@abstract
class AbstractBase:
    pass


@injectable
class ConcreteImpl(AbstractBase):
    pass


@injectable(lifetime="transient")
class ServiceDependsOnAbstract:
    def __init__(self, dep: AbstractBase):
        self.dep = dep


class Proto(Protocol):
    def method(self): ...


@injectable(as_type=Proto)
class ProtoImpl:
    def method(self):
        return "impl"


@injectable(lifetime="transient")
class ServiceDependsOnProto:
    def __init__(self, dep: Proto):
        self.dep = dep


def test_override_abstract_direct():
    container = create_sync_container(injectables=[AbstractBase, ConcreteImpl])

    mock_obj = MagicMock(spec=AbstractBase)

    @inject_from_container(container)
    def get_abstract_via_inject(svc: Injected[AbstractBase]) -> AbstractBase:
        return svc

    with container.override.injectable(target=AbstractBase, new=mock_obj):
        assert container.get(AbstractBase) is mock_obj
        assert get_abstract_via_inject() is mock_obj

    assert isinstance(container.get(AbstractBase), ConcreteImpl)
    assert isinstance(get_abstract_via_inject(), ConcreteImpl)


def test_override_abstract_indirect():
    container = create_sync_container(injectables=[AbstractBase, ConcreteImpl, ServiceDependsOnAbstract])

    mock_obj = MagicMock(spec=AbstractBase)

    @inject_from_container(container)
    def get_svc_via_inject(svc: Injected[ServiceDependsOnAbstract]) -> ServiceDependsOnAbstract:
        return svc

    with container.override.injectable(target=AbstractBase, new=mock_obj):
        with container.enter_scope() as scope:
            svc = scope.get(ServiceDependsOnAbstract)
            assert svc.dep is mock_obj
            assert get_svc_via_inject().dep is mock_obj

    with container.enter_scope() as scope:
        svc = scope.get(ServiceDependsOnAbstract)
        assert isinstance(svc.dep, ConcreteImpl)
        assert isinstance(get_svc_via_inject().dep, ConcreteImpl)


async def test_override_abstract_indirect_async():
    container = create_async_container(injectables=[AbstractBase, ConcreteImpl, ServiceDependsOnAbstract])

    mock_obj = MagicMock(spec=AbstractBase)

    @inject_from_container(container)
    async def get_svc_via_inject(svc: Injected[ServiceDependsOnAbstract]) -> ServiceDependsOnAbstract:
        return svc

    with container.override.injectable(target=AbstractBase, new=mock_obj):
        async with container.enter_scope() as scope:
            svc = await scope.get(ServiceDependsOnAbstract)
            assert svc.dep is mock_obj
            assert (await get_svc_via_inject()).dep is mock_obj

    async with container.enter_scope() as scope:
        svc = await scope.get(ServiceDependsOnAbstract)
        assert isinstance(svc.dep, ConcreteImpl)
        assert isinstance((await get_svc_via_inject()).dep, ConcreteImpl)


def test_override_as_type_direct():
    container = create_sync_container(injectables=[ProtoImpl])

    mock_obj = MagicMock(spec=Proto)

    @inject_from_container(container)
    def get_proto_via_inject(svc: Injected[Proto]) -> Proto:
        return svc

    with container.override.injectable(target=Proto, new=mock_obj):
        assert container.get(Proto) is mock_obj
        assert get_proto_via_inject() is mock_obj

    assert isinstance(container.get(Proto), ProtoImpl)
    assert isinstance(get_proto_via_inject(), ProtoImpl)


def test_override_as_type_indirect():
    container = create_sync_container(injectables=[ProtoImpl, ServiceDependsOnProto])

    mock_obj = MagicMock(spec=Proto)

    @inject_from_container(container)
    def get_svc_via_inject(svc: Injected[ServiceDependsOnProto]) -> ServiceDependsOnProto:
        return svc

    with container.override.injectable(target=Proto, new=mock_obj):
        with container.enter_scope() as scope:
            svc = scope.get(ServiceDependsOnProto)
            assert svc.dep is mock_obj
            assert get_svc_via_inject().dep is mock_obj

    with container.enter_scope() as scope:
        svc = scope.get(ServiceDependsOnProto)
        assert isinstance(svc.dep, ProtoImpl)
        assert isinstance(get_svc_via_inject().dep, ProtoImpl)


async def test_override_as_type_indirect_async():
    container = create_async_container(injectables=[ProtoImpl, ServiceDependsOnProto])

    mock_obj = MagicMock(spec=Proto)

    @inject_from_container(container)
    async def get_svc_via_inject(svc: Injected[ServiceDependsOnProto]) -> ServiceDependsOnProto:
        return svc

    with container.override.injectable(target=Proto, new=mock_obj):
        async with container.enter_scope() as scope:
            svc = await scope.get(ServiceDependsOnProto)
            assert svc.dep is mock_obj
            assert (await get_svc_via_inject()).dep is mock_obj

    async with container.enter_scope() as scope:
        svc = await scope.get(ServiceDependsOnProto)
        assert isinstance(svc.dep, ProtoImpl)
        assert isinstance((await get_svc_via_inject()).dep, ProtoImpl)


def test_override_restores_singleton_rebound_factory_sync():
    container = create_sync_container(injectables=[Foo, FooImpl])
    obj_id = FactoryCompiler.get_object_id(Foo, None)

    original_instance = container.get(Foo)
    rebound_factory = container._compiler.factories[obj_id].factory

    mock_obj = MagicMock(spec=Foo)
    with container.override.injectable(target=Foo, new=mock_obj):
        assert container.get(Foo) is mock_obj
        assert container._compiler.factories[obj_id].factory is not rebound_factory

    assert container.get(Foo) is original_instance
    assert container._compiler.factories[obj_id].factory is rebound_factory


async def test_override_restores_singleton_rebound_factory_async():
    @wireup.injectable
    async def async_foo_factory() -> FooBar:
        return FooBar()

    container = create_async_container(injectables=[async_foo_factory])
    obj_id = FactoryCompiler.get_object_id(FooBar, None)

    original_instance = await container.get(FooBar)
    rebound_factory = container._compiler.factories[obj_id].factory

    mock_obj = MagicMock()
    with container.override.injectable(target=FooBar, new=mock_obj):
        assert await container.get(FooBar) is mock_obj
        assert container._compiler.factories[obj_id].factory is not rebound_factory

    assert await container.get(FooBar) is original_instance
    assert container._compiler.factories[obj_id].factory is rebound_factory
