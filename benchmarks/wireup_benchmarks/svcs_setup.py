from contextlib import asynccontextmanager
from typing import Dict

import fastapi
import svcs
from svcs.fastapi import DepContainer

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings

router = fastapi.APIRouter()

# Factories need to adapt Svcs's expectation of (args) -> Service
# or be manually registered.

# Svcs factory registration:
# reg.register_factory(ServiceType, factory_function, on_registry_close=None)

# For A:
# services.make_a(settings: Settings) -> A
# We can register Settings as a value, then invoke make_a from container.

registry = svcs.Registry()

# Register singletons
# Settings doesn't depend on anything, but we need to pass it to make_a
settings_instance = Settings()
registry.register_value(Settings, settings_instance)

# A depends on Settings.
a_instance = services.make_a(settings_instance)
registry.register_value(A, a_instance)

# B depends on A
b_instance = services.B(a_instance)
registry.register_value(B, b_instance)

# Scoped Services (per request)
# In Svcs, "scoped" is managed by the request lifecycle.
# The DepContainer gives us a request-scoped container.
# However, register_factory is global.


# C()
def factory_c(container: svcs.Container):
    return services.C()


registry.register_factory(C, factory_c)


# D(c: C)
def factory_d(container: svcs.Container):
    return services.D(c=container.get(C))


registry.register_factory(D, factory_d)


# E(c: C, d: D)
def factory_e(container: svcs.Container):
    return services.E(
        c=container.get(C),
        d=container.get(D),
    )


registry.register_factory(E, factory_e)


# F(c: C, d: D, e: E)
def factory_f(container: svcs.Container):
    return services.F(
        c=container.get(C),
        d=container.get(D),
        e=container.get(E),
    )


registry.register_factory(F, factory_f)


# G(c: C, d: D, e: E, f: F)
def factory_g(container: svcs.Container):
    return services.G(
        c=container.get(C),
        d=container.get(D),
        e=container.get(E),
        f=container.get(F),
    )


registry.register_factory(G, factory_g)

# H and I use generators (make_h, make_i)
# Svcs supports generators out of the box.


# make_h(c: C, d: D) -> Iterator[H]
def factory_h(container: svcs.Container):
    yield from services.make_h(
        c=container.get(C),
        d=container.get(D),
    )


registry.register_factory(H, factory_h)


# make_i(e: E, f: F) -> AsyncIterator[I]
async def factory_i(container: svcs.Container):
    async for i in services.make_i(
        e=await container.aget(E),
        f=await container.aget(F),
    ):
        yield i


registry.register_factory(I, factory_i)

# Register all factories in a loop or helper if possible?
# But explicit is okay for this file.


@asynccontextmanager
async def _lifespan(app: fastapi.FastAPI, registry: svcs.Registry):
    yield {}


lifespan = svcs.fastapi.lifespan(_lifespan, registry=registry)


@router.get("/svcs/singleton")
async def svcs_singleton(container: DepContainer) -> Dict[str, str]:
    services.record_request("singleton")
    a = container.get(A)
    b = container.get(B)

    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/svcs/scoped")
async def svcs_scoped(container: DepContainer) -> Dict[str, str]:
    services.record_request("scoped")
    c = container.get(C)
    cc = container.get(C)
    ccc = container.get(C)
    d = container.get(D)
    dd = container.get(D)
    e = container.get(E)
    f = container.get(F)
    g = container.get(G)
    h = container.get(H)
    i = await container.aget(I)

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
