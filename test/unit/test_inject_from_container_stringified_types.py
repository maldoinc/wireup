from __future__ import annotations

from dataclasses import dataclass

import wireup
from wireup._annotations import Injected  # noqa: TC002


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
    def main(maybe_thing: Injected[MaybeThing | None], thing: Injected[Thing]):
        assert maybe_thing is None
        assert isinstance(thing, Thing)
        assert thing.maybe_thing is None

    main()
