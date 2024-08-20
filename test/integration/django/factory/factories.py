from django.conf import settings
from wireup import service

from test.integration.django.service.random_service import RandomService


@service
def _make_random_service() -> RandomService:
    return RandomService(settings.START_NUM)
