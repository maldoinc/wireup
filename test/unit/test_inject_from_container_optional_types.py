from dataclasses import dataclass
from typing import Optional, Union

import pytest
import wireup
from typing_extensions import Annotated
from wireup._annotations import Inject, Injected
from wireup.errors import DuplicateServiceRegistrationError


class MaybeThing: ...


@dataclass
class Thing:
    maybe_thing: Optional[MaybeThing] = None


def test_inject_from_container_handles_optionals() -> None:
    def make_maybe_thing() -> Optional[MaybeThing]:
        return None

    def make_thing(maybe_thing: Optional[MaybeThing]) -> Thing:
        return Thing(maybe_thing=maybe_thing)

    container = wireup.create_sync_container(
        services=[wireup.injectable(make_maybe_thing), wireup.injectable(make_thing)]
    )

    @wireup.inject_from_container(container)
    def main(
        maybe_thing: Injected[Optional[MaybeThing]],
        maybe_thing_annotated: Annotated[Optional[MaybeThing], Inject(qualifier=None)],
        maybe_thing_annotated2: Optional[Annotated[MaybeThing, Inject(qualifier=None)]],
        maybe_thing_annotated3: Union[Annotated[MaybeThing, Inject(qualifier=None)], None],
        maybe_thing_annotated4: Annotated[Union[MaybeThing, None], Inject(qualifier=None)],
        thing: Injected[Thing],
    ):
        assert maybe_thing is None
        assert maybe_thing_annotated is None
        assert maybe_thing_annotated2 is None
        assert maybe_thing_annotated3 is None
        assert maybe_thing_annotated4 is None
        assert isinstance(thing, Thing)
        assert thing.maybe_thing is None

    main()


def test_getting_optional_service_via_plain_type_emits_deprecation_warning() -> None:
    @wireup.injectable
    class Foo:
        pass

    @wireup.injectable
    def make_foo() -> Optional[Foo]:
        return Foo()

    container = wireup.create_sync_container(services=[make_foo])

    with pytest.warns(DeprecationWarning) as record:
        inst = container.get(Foo)

    assert len(record) == 1
    assert "registered as optional" in str(record[0].message)

    assert inst is container.get(Optional[Foo])


def test_registering_optional_and_plain_type_raises_duplicate() -> None:
    @wireup.injectable
    class Foo:
        pass

    @wireup.injectable
    def make_optional() -> Optional[Foo]:
        return None

    # Registering both an Optional[T] factory and a T factory together raises since
    # wireup will add a backwards-compatible factory for T when registering it as optional.
    with pytest.raises(DuplicateServiceRegistrationError):
        wireup.create_sync_container(services=[make_optional, Foo])
