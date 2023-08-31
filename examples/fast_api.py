import os
import random
from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI
from wireup import container

import examples.services
from examples.services.db_service import DbService

app = FastAPI()


@container.register
@dataclass
class DummyService:
    # For dataclasses you don't even need a ctor, they will be auto-injected. @dataclass MUST be placed BEFORE register.
    db: DbService

    # Parameters cannot be located from type alone, so they need some more information.
    env: str = wire(param="env")  # Get parameter with this value
    logs_cache_dir: str = wire(expr="${cache_dir}/logs")  # Interpolate parameters within curly brackets

    def dummy(self):
        return f"Running in env={self.env}; db={self.db.get_result()}"


# Another service which doesn't have dependencies but can greet people in many languages
@container.register
class GreeterService:
    @staticmethod
    def greet(name: str) -> str:
        return "{} {}".format(random.choice(["Hi", "Oye", "Përshëndetje", "Guten Tag"]), name)


@app.get("/")
@wire
async def root(
    name: Optional[str] = None,  # This is a fastapi query parameter
    # The default value is not needed by the container. It is only to make fastapi happy.
    # It is the equivalent of Depends(lambda: None) and will have to be used for any deps that are to be injected
    dummy_service: DummyService = wire(),
    # This will have precedence over fastapi and will not contain the value found in query string.
    logs_cache_dir: str = wire(expr="${cache_dir}/logs"),
):
    # If you really need to, you can also get services this way.
    # Although injection is the recommended way this is left available for cases
    # where dynamic loading of some sort is required
    greeter: GreeterService = container.get(GreeterService)

    return {
        "greeting": greeter.greet(name),
        "cache_dir": logs_cache_dir,
        "dummy": dummy_service.dummy(),
    }


# Register parameters in the container
container.register_all_in_module(examples.services)
container.params.put("connection_str", "sqlite")
container.params.put("cache_dir", "/var/cache")
container.params.put("env", "prod")
container.params.put("auth.user", "anon")
container.params.update(dict(os.environ))

for k, v in container.params.get_all().items():
    print(f"> {k}={v}")
