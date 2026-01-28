from typing import Protocol
from unittest.mock import MagicMock

from wireup import abstract, create_async_container, create_sync_container, injectable


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

    with container.override.injectable(target=AbstractBase, new=mock_obj):
        assert container.get(AbstractBase) is mock_obj

    assert isinstance(container.get(AbstractBase), ConcreteImpl)


def test_override_abstract_indirect():
    container = create_sync_container(injectables=[AbstractBase, ConcreteImpl, ServiceDependsOnAbstract])

    mock_obj = MagicMock(spec=AbstractBase)

    with container.override.injectable(target=AbstractBase, new=mock_obj):
        with container.enter_scope() as scope:
            svc = scope.get(ServiceDependsOnAbstract)
            assert svc.dep is mock_obj

    with container.enter_scope() as scope:
        svc = scope.get(ServiceDependsOnAbstract)
        assert isinstance(svc.dep, ConcreteImpl)


async def test_override_abstract_indirect_async():
    container = create_async_container(injectables=[AbstractBase, ConcreteImpl, ServiceDependsOnAbstract])

    mock_obj = MagicMock(spec=AbstractBase)

    with container.override.injectable(target=AbstractBase, new=mock_obj):
        async with container.enter_scope() as scope:
            svc = await scope.get(ServiceDependsOnAbstract)
            assert svc.dep is mock_obj

    async with container.enter_scope() as scope:
        svc = await scope.get(ServiceDependsOnAbstract)
        assert isinstance(svc.dep, ConcreteImpl)


def test_override_as_type_direct():
    container = create_sync_container(injectables=[ProtoImpl])

    mock_obj = MagicMock(spec=Proto)

    with container.override.injectable(target=Proto, new=mock_obj):
        assert container.get(Proto) is mock_obj

    assert isinstance(container.get(Proto), ProtoImpl)


def test_override_as_type_indirect():
    container = create_sync_container(injectables=[ProtoImpl, ServiceDependsOnProto])

    mock_obj = MagicMock(spec=Proto)

    with container.override.injectable(target=Proto, new=mock_obj):
        with container.enter_scope() as scope:
            svc = scope.get(ServiceDependsOnProto)
            assert svc.dep is mock_obj

    with container.enter_scope() as scope:
        svc = scope.get(ServiceDependsOnProto)
        assert isinstance(svc.dep, ProtoImpl)


async def test_override_as_type_indirect_async():
    container = create_async_container(injectables=[ProtoImpl, ServiceDependsOnProto])

    mock_obj = MagicMock(spec=Proto)

    with container.override.injectable(target=Proto, new=mock_obj):
        async with container.enter_scope() as scope:
            svc = await scope.get(ServiceDependsOnProto)
            assert svc.dep is mock_obj

    async with container.enter_scope() as scope:
        svc = await scope.get(ServiceDependsOnProto)
        assert isinstance(svc.dep, ProtoImpl)
