import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import FastAPI

from wireup_benchmarks import dependency_injector_setup, fastapi_setup, wireup_setup

container = wireup.create_async_container(service_modules=[wireup_setup], parameters={"start": 10})
app = FastAPI(router="")


app.include_router(fastapi_setup.router)
app.include_router(wireup_setup.router)

app.container = dependency_injector_setup.container
app.include_router(dependency_injector_setup.router)

wireup.integration.fastapi.setup(container, app)
