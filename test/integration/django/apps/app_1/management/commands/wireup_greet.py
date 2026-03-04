from typing import Any

from django.core.management.base import BaseCommand
from wireup import Injected
from wireup.integration.django import inject_app

from test.shared.shared_services.greeter import GreeterService


class Command(BaseCommand):
    help = "Greet using a Wireup-injected dependency."

    def add_arguments(self, parser: Any):
        parser.add_argument("--name", default="World")

    @inject_app
    def handle(self, *_args: Any, name: str, greeter: Injected[GreeterService], **_options: Any):
        self.stdout.write(greeter.greet(name))
