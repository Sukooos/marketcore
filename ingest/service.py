from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ingest.metrics import IngestMetrics
from ingest.publisher import RedisPublisher


@dataclass(slots=True)
class ServiceStatus:
    service: str = "ingest"
    redis_connected: bool = False
    published_events: int = 0


class IngestService:
    def __init__(
        self,
        *,
        status: ServiceStatus | None = None,
        metrics: IngestMetrics | None = None,
        publisher: RedisPublisher | None = None,
    ) -> None:
        self._status = status or ServiceStatus()
        self._metrics = metrics or IngestMetrics(
            published_events=self._status.published_events,
            redis_connected=self._status.redis_connected,
        )
        self._publisher = publisher
        self._metrics.set_redis_connected(self._status.redis_connected)

    def set_redis_connected(self, connected: bool) -> None:
        self._metrics.set_redis_connected(connected)
        self._status = replace(self._status, redis_connected=connected)

    def status(self) -> ServiceStatus:
        return replace(
            self._status,
            redis_connected=self._metrics.redis_connected,
            published_events=self._metrics.published_events,
        )

    def health_payload(self) -> dict[str, object]:
        snapshot = self.status()
        return {
            "service": snapshot.service,
            "healthy": snapshot.redis_connected,
            "redis_connected": snapshot.redis_connected,
            "published_events": snapshot.published_events,
        }

    async def publish_event(self, event: Any) -> int:
        if self._publisher is None:
            raise RuntimeError("publisher is not configured")

        receivers = await self._publisher.publish(event)
        self._metrics.record_publication()
        self._status = replace(self._status, published_events=self._metrics.published_events)
        return receivers
