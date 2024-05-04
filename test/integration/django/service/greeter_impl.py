from test.integration.django.service.greeter_interface import GreeterService

from wireup import container


@container.register
class GreeterServiceImpl(GreeterService):
    def greet(self, name: str) -> str:
        return f"Hello {name}"
