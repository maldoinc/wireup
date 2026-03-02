import os

from fastapi import FastAPI, HTTPException

from wireup_benchmarks import services

app = FastAPI(router="")
project = os.environ["PROJECT"]


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/assert-workload")
async def assert_workload():
    ok, expected, counters, mismatches = services.assert_workload()
    if not ok:
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "expected": expected, "counters": counters, "mismatches": mismatches},
        )
    return {"ok": True, "expected": expected, "counters": counters, "mismatches": mismatches}


if project == "dependency_injector":
    from wireup_benchmarks import dependency_injector_setup

    app.container = dependency_injector_setup.container  # type: ignore[attr-defined]
    app.include_router(dependency_injector_setup.router)
elif project == "fastapi":
    from wireup_benchmarks import fastapi_setup

    app.include_router(fastapi_setup.router)
elif project == "wireup":
    import wireup.integration.fastapi

    from wireup_benchmarks import wireup_setup

    app.include_router(wireup_setup.router)
    wireup.integration.fastapi.setup(wireup_setup.container, app)
elif project == "wireup_cbr":
    import wireup.integration.fastapi

    from wireup_benchmarks import wireup_setup
    from wireup_benchmarks.wireup_cbr_setup import WireupScopedBenchController, WireupSingletonBenchController

    wireup.integration.fastapi.setup(
        wireup_setup.container,
        app,
        class_based_handlers=[WireupSingletonBenchController, WireupScopedBenchController],
    )
elif project == "globals":
    from wireup_benchmarks import globals_setup

    app.include_router(globals_setup.router)
elif project == "aioinject":
    from aioinject.ext.fastapi import AioInjectMiddleware

    from wireup_benchmarks import aioinject_setup

    app.add_middleware(AioInjectMiddleware, container=aioinject_setup.container)
    app.include_router(aioinject_setup.router)
elif project == "dishka":
    from dishka.integrations.fastapi import setup_dishka

    from wireup_benchmarks import dishka_setup

    app.include_router(dishka_setup.router)
    setup_dishka(dishka_setup.container, app)
elif project == "lagom":
    from wireup_benchmarks import lagom_setup

    app.include_router(lagom_setup.router)
elif project == "injector":
    from wireup_benchmarks import injector_setup

    app.include_router(injector_setup.router)
    injector_setup.setup_injector(app)
elif project == "svcs":
    from wireup_benchmarks import svcs_setup

    app.include_router(svcs_setup.router)
    app.router.lifespan_context = svcs_setup.lifespan
elif project == "that_depends":
    from that_depends.providers import DIContextMiddleware

    from wireup_benchmarks import that_depends_setup

    app.add_middleware(
        DIContextMiddleware, that_depends_setup.Container, scope=that_depends_setup.ContextScopes.REQUEST
    )
    app.include_router(that_depends_setup.router)
elif project == "diwire":
    from wireup_benchmarks import diwire_setup

    app.include_router(diwire_setup.router)
