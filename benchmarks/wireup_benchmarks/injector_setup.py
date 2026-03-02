from typing import Dict

import fastapi
from fastapi_injector import (
    Injected,
    InjectorMiddleware,
    RequestScopeOptions,
    attach_injector,
    request_scope,
)
from injector import Injector, Module, provider, singleton

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings


class BenchmarkModule(Module):
    """Module that configures all services for the benchmark."""

    # Singletons
    @singleton
    @provider
    def provide_settings(self) -> Settings:
        return Settings()

    @singleton
    @provider
    def provide_a(self, settings: Settings) -> A:
        return A(settings.start)

    @singleton
    @provider
    def provide_b(self, a: A) -> B:
        return B(a)

    # Scoped services (request scope)
    @request_scope
    @provider
    def provide_c(self) -> C:
        return C()

    @request_scope
    @provider
    def provide_d(self, c: C) -> D:
        return D(c)

    @request_scope
    @provider
    def provide_e(self, c: C, d: D) -> E:
        return E(c, d)

    @request_scope
    @provider
    def provide_f(self, c: C, d: D, e: E) -> F:
        return F(c, d, e)

    @request_scope
    @provider
    def provide_g(self, c: C, d: D, e: E, f: F) -> G:
        return G(c, d, e, f)

    # H is a sync generator in the original - provide as scoped
    @request_scope
    @provider
    def provide_h(self, c: C, d: D) -> H:
        return H(c, d)

    # I is an async generator in the original - provide as scoped
    @request_scope
    @provider
    def provide_i(self, e: E, f: F) -> I:
        return I(e, f)


injector = Injector([BenchmarkModule()])
router = fastapi.APIRouter()


def setup_injector(app: fastapi.FastAPI) -> None:
    """Setup injector middleware and attach to app."""
    app.add_middleware(InjectorMiddleware, injector=injector)
    options = RequestScopeOptions(enable_cleanup=True)
    attach_injector(app, injector, options)


@router.get("/injector/singleton")
async def injector_singleton(
    a: A = Injected(A),
    b: B = Injected(B),
) -> Dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/injector/scoped")
async def injector_scoped(
    c: C = Injected(C),
    cc: C = Injected(C),
    ccc: C = Injected(C),
    d: D = Injected(D),
    dd: D = Injected(D),
    e: E = Injected(E),
    f: F = Injected(F),
    g: G = Injected(G),
    h: H = Injected(H),
    i: I = Injected(I),
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
