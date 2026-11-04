import warnings
from dataclasses import dataclass
from typing import Annotated, Optional

import wireup
from wireup._annotations import Inject, Injected


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


def test_getting_optional_service_via_plain_type_resolves_silently() -> None:
    class Foo:
        pass

    def make_foo() -> Foo | None:
        return Foo()

    container = wireup.create_sync_container(injectables=[wireup.injectable(make_foo)])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inst = container.get(Foo)

    assert isinstance(inst, Foo)
    assert inst is container.get(optional_hint(Foo))
    assert inst is container.get(Foo | None)


async def test_getting_optional_service_via_plain_type_resolves_silently_async() -> None:
    class Foo:
        pass

    def make_foo() -> Foo | None:
        return Foo()

    container = wireup.create_async_container(injectables=[wireup.injectable(make_foo)])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inst = await container.get(Foo)

    assert isinstance(inst, Foo)
    assert inst is await container.get(Foo | None)


def test_getting_qualified_optional_service_via_plain_type_keeps_qualifier() -> None:
    # https://github.com/maldoinc/wireup/issues/138
    # A qualified Optional[T] factory must keep its qualifier so container.get(T, qualifier=...)
    # resolves it instead of failing with a spurious self-dependency error.
    class Foo:
        pass

    @wireup.injectable(qualifier="primary")
    def make_foo() -> Foo | None:
        return Foo()

    container = wireup.create_sync_container(injectables=[make_foo])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inst = container.get(Foo, qualifier="primary")

    assert isinstance(inst, Foo)
    assert inst is container.get(Foo | None, qualifier="primary")


def test_registering_optional_and_plain_type_are_distinct() -> None:
    class Foo:
        pass

    def make_optional() -> Foo | None:
        return None

    def make_plain() -> Foo:
        return Foo()

    # The Optional[T] factory and a plain T factory are distinct registration keys:
    # T | None and T no longer collide, so retrieving each returns its own instance
    # and container.get(T) resolves the plain factory directly (not the optional fallback).
    container = wireup.create_sync_container(
        injectables=[wireup.injectable(make_optional), wireup.injectable(make_plain)]
    )

    assert container.get(Foo | None) is None
    assert isinstance(container.get(Foo), Foo)
