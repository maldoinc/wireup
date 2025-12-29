from wireup import injectable


@injectable
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello {name}"


@injectable
class AsyncGreeterService(GreeterService):
    async def agreet(self, name: str) -> str:
        return super().greet(name)
