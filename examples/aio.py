import random

from aiohttp import web
from wireup import container


@container.register
class GreeterService:
    def greet(self, name: str) -> str:
        return "{} {}".format(random.choice(["Hi", "Oye", "Përshëndetje", "Guten Tag"]), name)


@container.autowire
async def handle(request, greeter: GreeterService, cache_dir=wire(param="cache_dir")):
    name = request.match_info.get("name", "Anonymous")

    return web.Response(text=f"{greeter.greet(name)}, cache is located in {cache_dir}")


app = web.Application()
app.add_routes([web.get("/", handle), web.get("/{name}", handle)])

container.params.put("cache_dir", "/var/cache")

if __name__ == "__main__":
    web.run_app(app)
