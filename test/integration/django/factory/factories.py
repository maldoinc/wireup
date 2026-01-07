from django.conf import settings
from wireup import injectable

from test.integration.django.injectable.random_service import RandomService


@injectable
def _make_random_service() -> RandomService:
    return RandomService(settings.START_NUM)
