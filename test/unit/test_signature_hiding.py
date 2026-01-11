import inspect

from typing_extensions import Annotated
from wireup import Injected, create_sync_container, inject_from_container, service
from wireup._decorators import inject_from_container_unchecked


def test_inject_from_container_hides_annotated_parameters():
    @service
    class Service:
        pass

    container = create_sync_container(injectables=[Service])

    @inject_from_container(container, hide_annotated_names=True)
    def foo(param1: str, service: Injected[Service]):
        return param1, service

    sig = inspect.signature(foo)
    assert "service" not in sig.parameters
    assert "param1" in sig.parameters

    assert foo.__wireup_names__ is not None
    assert "service" in foo.__wireup_names__

    res_param, res_service = foo(param1="value")
    assert res_param == "value"
    assert isinstance(res_service, Service)


def test_inject_from_container_unchecked_hides_annotated_parameters():
    @service
    class Service:
        pass

    container = create_sync_container(injectables=[Service])

    def supplier():
        return container.enter_scope()

    @inject_from_container_unchecked(supplier, hide_annotated_names=True)
    def bar(param1: str, service: Injected[Service]):
        return param1, service

    sig = inspect.signature(bar)
    assert "service" not in sig.parameters
    assert "param1" in sig.parameters

    res_param, res_service = bar(param1="value")
    assert res_param == "value"
    assert isinstance(res_service, Service)


def test_default_behavior_preserves_signature():
    @service
    class Service:
        pass

    container = create_sync_container(injectables=[Service])

    @inject_from_container(container)
    def baz(param1: str, service: Injected[Service]):
        return param1, service

    sig = inspect.signature(baz)
    assert "service" in sig.parameters
    assert "param1" in sig.parameters

    res_param, res_service = baz(param1="value")
    assert res_param == "value"
    assert isinstance(res_service, Service)
