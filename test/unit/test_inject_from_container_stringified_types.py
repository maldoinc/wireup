from __future__ import annotations

from dataclasses import dataclass

import wireup
from typing_extensions import Annotated
from wireup import Inject, Injected


class MaybeThing: ...


@dataclass
class Thing:
    maybe_thing: MaybeThing | None = None


def test_inject_from_container_handles_optionals() -> None:
    def make_maybe_thing() -> MaybeThing | None:
        return None

    def make_thing(maybe_thing: MaybeThing | None) -> Thing:
        return Thing(maybe_thing=maybe_thing)

    container = wireup.create_sync_container(services=[wireup.service(make_maybe_thing), wireup.service(make_thing)])

    @wireup.inject_from_container(container)
    def main(
        maybe_thing: Injected[MaybeThing | None],
        maybe_thing_annotated: Annotated[MaybeThing | None, Inject(qualifier=None)],
        maybe_thing_annotated2: Annotated[MaybeThing, Inject(qualifier=None)] | None,
        thing: Injected[Thing],
    ):
        assert maybe_thing is None
        assert maybe_thing_annotated is None
        assert maybe_thing_annotated2 is None
        assert isinstance(thing, Thing)
        assert thing.maybe_thing is None

    main()
