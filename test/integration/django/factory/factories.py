from test.integration.django.service.random_service import RandomService

from django.conf import settings
from wireup import container


@container.register
def _make_random_service() -> RandomService:
    return RandomService(settings.START_NUM)
