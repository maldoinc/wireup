The example below shows a simple implementation in a FastAPI application. 
The concepts are generic enough to be applicable to other python frameworks as well.

```python
import os
import random
from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI
from wireup import container, wire

app = FastAPI()


# Dependency that can greet in many languages
@container.register
class GreeterService:
    @staticmethod
    def greet(name: str) -> str:
        greeting = random.choice(["Hi", "Oye", "Përshëndetje", "Guten Tag"])
        
        return f"{greeting} {name}"


@container.register
@dataclass
class DummyService:
    # Dataclass attributes will be automatically injected if known by the container.
    greeter: GreeterService

    # Parameters cannot be located from type alone, so they need some more information.
    # Get parameter with a given name.
    env: str = wire(param="env")
    # Interpolate parameters within curly brackets.
    logs_cache_dir: str = wire(expr="${cache_dir}/logs")

    def dummy(self):
        return f"Running in env={self.env}; Storing cache in {self.logs_cache_dir}"


@app.get("/")
@container.autowire
async def root(
    # This is a FastAPI query parameter.
    name: Optional[str] = None,  
    # Default value is not needed by the container, it is only to make FastAPI happy.
    # It is the equivalent of Depends(lambda: None)
    # and will have to be used for any deps that are to be injected.
    # When using other frameworks the wire() call can be omitted.
    dummy_service: DummyService = wire(),
    logs_cache_dir: str = wire(expr="${cache_dir}/logs"),
):
    # If you really need to, you can also get dependencies this way.
    # And use the container in a service locator manner.
    # Although injection is the recommended way this is left available for cases
    # where dynamic loading of some sort is required.
    # This however is still a hard dependency that is not getting injected.
    greeter = container.get(GreeterService)

    return {
        "greeting": greeter.greet(name),
        "cache_dir": logs_cache_dir,
        "dummy": dummy_service.dummy(),
    }


# Register individual parameters in the container
container.params.put("cache_dir", "/var/cache")
container.params.put("env", "prod")
container.params.put("auth.user", "anon")
# Merge current values using the ones from the dict.
container.params.update(dict(os.environ))

```
