from __future__ import annotations

from typing import Iterator

from typing_extensions import Annotated
from wireup import Inject, injectable


class HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url


@injectable
def make_http_client(
    weather_url: Annotated[str, Inject(config="services.weather.base_url")],
) -> Iterator[HttpClient]:
    yield HttpClient(weather_url)
