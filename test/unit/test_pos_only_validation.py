import pytest
from typing_extensions import Annotated
from wireup import Inject, create_sync_container, inject_from_container, injectable
from wireup.errors import PositionalOnlyParameterError


def test_service_with_pos_only_arg_raises_error():
    @injectable
    def my_service(dep: Annotated[str, Inject(config="foo")], /) -> str:
        return dep

    with pytest.raises(PositionalOnlyParameterError):
        create_sync_container(injectables=[my_service], config={"foo": "bar"})


def test_service_class_with_pos_only_arg_raises_error():
    @injectable
    class MyService:
        def __init__(self, dep: Annotated[str, Inject(config="foo")], /) -> None:
            pass

    with pytest.raises(PositionalOnlyParameterError):
        create_sync_container(injectables=[MyService], config={"foo": "bar"})


def test_inject_from_container_pos_only_injected_param_raises_error():
    container = create_sync_container(config={"foo": "bar"})

    with pytest.raises(PositionalOnlyParameterError):

        @inject_from_container(container)
        def target(dep: Annotated[str, Inject(config="foo")], /):
            pass


def test_inject_from_container_manual_pos_only_param_succeeds():
    container = create_sync_container(config={"foo": "bar"})

    @inject_from_container(container)
    def target(manual: str, /, dep: Annotated[str, Inject(config="foo")]):
        return manual, dep

    assert target("manual") == ("manual", "bar")
