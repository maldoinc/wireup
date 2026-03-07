from __future__ import annotations

from typing_extensions import Annotated

from wireup import Inject, injectable


@injectable
class RedisConnection:
    def __init__(self, dsn: Annotated[str, Inject(config="infra.redis.url")]) -> None:
        self.dsn = dsn


@injectable
class MetricsClient:
    def __init__(self, endpoint: Annotated[str, Inject(config="infra.metrics.endpoint")]) -> None:
        self.endpoint = endpoint


@injectable
class KeyValueStore:
    def __init__(self, redis: RedisConnection, metrics: MetricsClient) -> None:
        self.redis = redis
        self.metrics = metrics
