from wireup import service


@service
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello {name}"
