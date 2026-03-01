from django.core.management.base import BaseCommand
from wireup import Injected
from wireup.integration.django import inject_app

from test.shared.shared_services.greeter import GreeterService


class Command(BaseCommand):
    help = "Greet using a Wireup-injected dependency."

    def add_arguments(self, parser):
        parser.add_argument("--name", default="World")

    @inject_app
    def handle(self, *args, name: str, greeter: Injected[GreeterService], **options):
        self.stdout.write(greeter.greet(name))
