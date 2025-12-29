from __future__ import annotations

import wireup


@wireup.service
class Thing: ...


class Base:
    def __init__(self, thing: Thing) -> None:
        self.thing = thing
