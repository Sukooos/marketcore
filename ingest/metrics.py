from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import Counter, Gauge


published_events_total = Counter(
    "marketcore_published_events_total",
    "Total canonical events published to Redis.",
)
redis_connection_status = Gauge(
    "marketcore_redis_connection_status",
    "Redis connectivity status for the ingest service.",
)


@dataclass(slots=True)
class IngestMetrics:
    published_events: int = 0
    redis_connected: bool = False

    def set_redis_connected(self, connected: bool) -> None:
        self.redis_connected = connected
        redis_connection_status.set(1 if connected else 0)

    def record_publication(self, count: int = 1) -> None:
        self.published_events += count
        published_events_total.inc(count)
