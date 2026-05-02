from dataclasses import dataclass
from typing import Annotated, Optional, Union

import pytest
import wireup
from wireup._annotations import Inject, Injected
from wireup.errors import DuplicateServiceRegistrationError


class MaybeThing: ...


@dataclass
class Thing:
    maybe_thing: MaybeThing | None = None


def optional_hint(tp: object) -> object:
    return Optional.__getitem__(tp)


def test_inject_from_container_handles_optionals() -> None:
    def make_maybe_thing() -> MaybeThing | None:
        return None

    def make_thing(maybe_thing: MaybeThing | None) -> Thing:
        return Thing(maybe_thing=maybe_thing)

    container = wireup.create_sync_container(
        injectables=[wireup.injectable(make_maybe_thing), wireup.injectable(make_thing)]
    )

    @wireup.inject_from_container(container)
    def main(
        maybe_thing: Injected[MaybeThing | None],
        maybe_thing_annotated: Annotated[MaybeThing | None, Inject(qualifier=None)],
        maybe_thing_annotated2: Annotated[MaybeThing, Inject(qualifier=None)] | None,
        maybe_thing_annotated3: Annotated[MaybeThing, Inject(qualifier=None)] | None,
        maybe_thing_annotated4: Annotated[MaybeThing | None, Inject(qualifier=None)],
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
    def make_foo() -> Foo | None:
        return Foo()

    container = wireup.create_sync_container(injectables=[make_foo])

    with pytest.warns(DeprecationWarning) as record:
        inst = container.get(Foo)

    assert len(record) == 1
    assert "registered as optional" in str(record[0].message)

    assert inst is container.get(optional_hint(Foo))
    assert inst is container.get(Foo | None)


def test_registering_optional_and_plain_type_raises_duplicate() -> None:
    @wireup.injectable
    class Foo:
        pass

    @wireup.injectable
    def make_optional() -> Foo | None:
        return None

    # Registering both an Optional[T] factory and a T factory together raises since
    # wireup will add a backwards-compatible factory for T when registering it as optional.
    with pytest.raises(DuplicateServiceRegistrationError):
        wireup.create_sync_container(injectables=[make_optional, Foo])
