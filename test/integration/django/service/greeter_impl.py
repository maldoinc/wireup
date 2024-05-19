from test.integration.django.service.greeter_interface import GreeterService

from wireup import service


@service
class GreeterServiceImpl(GreeterService):
    def greet(self, name: str) -> str:
        return f"Hello {name}"
