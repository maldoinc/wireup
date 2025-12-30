import pytest
from wireup import create_sync_container, injectable, service


def test_service_is_deprecated():
    with pytest.warns(FutureWarning, match="The @service decorator is deprecated"):

        @service
        class Foo:
            pass

    assert hasattr(Foo, "__wireup_registration__")


def test_service_and_injectable_are_compatible():
    @injectable
    class Foo:
        pass

    @injectable
    class Bar:
        def __init__(self, foo: Foo):
            self.foo = foo

    container = create_sync_container(injectables=[Foo, Bar])
    bar = container.get(Bar)
    assert isinstance(bar.foo, Foo)
