from wireup import service

from test.integration.django.service.greeter_interface import GreeterService


@service
class GreeterServiceImpl(GreeterService):
    def greet(self, name: str) -> str:
        return f"Hello {name}"
