from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse


class HealthService(Protocol):
    def health_payload(self) -> dict[str, object]: ...


class _DefaultService:
    def health_payload(self) -> dict[str, object]:
        return {
            "service": "api",
            "healthy": False,
            "redis_connected": False,
            "published_events": 0,
        }


def create_app(service: HealthService | None = None) -> FastAPI:
    ingest_service = service or _DefaultService()
    app = FastAPI(title="MarketCore API")

    @app.get("/health")
    async def health() -> dict[str, object]:
        return ingest_service.health_payload()

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(
            "# HELP marketcore_api_up API scaffold availability\n"
            "# TYPE marketcore_api_up gauge\n"
            "marketcore_api_up 1\n"
        )

    return app


app = create_app()
