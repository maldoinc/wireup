from wireup import service


@service
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello {name}"


@service
class AsyncGreeterService(GreeterService):
    async def agreet(self, name: str) -> str:
        return super().greet(name)
