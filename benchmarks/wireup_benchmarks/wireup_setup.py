from abc import ABC, abstractmethod
from typing import Dict, Mapping, Set

import fastapi
import wireup
from wireup import Injected
from wireup.integration.fastapi import WireupRoute

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I


class Plugin(ABC):
    @abstractmethod
    def label(self) -> str: ...


@wireup.injectable(as_type=Plugin, qualifier="red")
class PluginRed(Plugin):
    def label(self) -> str:
        return "red"


@wireup.injectable(as_type=Plugin, qualifier="green")
class PluginGreen(Plugin):
    def label(self) -> str:
        return "green"


@wireup.injectable(as_type=Plugin, qualifier="blue")
class PluginBlue(Plugin):
    def label(self) -> str:
        return "blue"


@wireup.injectable(as_type=Plugin, qualifier="alpha")
class PluginAlpha(Plugin):
    def label(self) -> str:
        return "alpha"


router = fastapi.APIRouter(route_class=WireupRoute)
container = wireup.create_async_container(
    services=[
        wireup.service(services.Settings),
        wireup.service(services.make_a),
        wireup.service(services.B),
        wireup.service(services.C, lifetime="scoped"),
        wireup.service(services.D, lifetime="scoped"),
        wireup.service(services.E, lifetime="scoped"),
        wireup.service(services.F, lifetime="scoped"),
        wireup.service(services.G, lifetime="scoped"),
        wireup.service(services.make_h, lifetime="scoped"),
        wireup.service(services.make_i, lifetime="scoped"),
        PluginRed,
        PluginGreen,
        PluginBlue,
        PluginAlpha,
    ],
    parameters={"start": 10},
)


@router.get("/wireup/singleton")
async def wireup_singleton(a: Injected[A], b: Injected[B]) -> Dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/wireup/scoped")
async def wireup_scoped(
    c: Injected[C],
    cc: Injected[C],
    ccc: Injected[C],
    d: Injected[D],
    dd: Injected[D],
    e: Injected[E],
    f: Injected[F],
    g: Injected[G],
    h: Injected[H],
    i: Injected[I],
) -> Dict[str, str]:
    services.record_request("scoped")
    assert isinstance(c, C)
    assert c is cc
    assert cc is ccc

    assert isinstance(d, D)
    assert isinstance(e, E)
    assert isinstance(f, F)
    assert isinstance(g, G)
    assert isinstance(h, H)
    assert isinstance(i, I)
    assert d is dd
    return {}


@router.get("/wireup/collection_set")
async def wireup_collection_set(plugins: Injected[Set[Plugin]]) -> Dict[str, str]:
    services.record_request("collection_set")
    assert len(plugins) == 4
    return {}


@router.get("/wireup/collection_map")
async def wireup_collection_map(plugins: Injected[Mapping[str, Plugin]]) -> Dict[str, str]:
    services.record_request("collection_map")
    assert set(plugins.keys()) == {"red", "green", "blue", "alpha"}
    return {}
