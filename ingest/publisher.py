from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def _normalize_event_payload(event: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(event, BaseModel):
        return event.model_dump(mode="json")
    return dict(event)


def encode_event_for_publication(event: BaseModel | Mapping[str, Any]) -> bytes:
    payload = _normalize_event_payload(event)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return encoded.encode("utf-8")


class RedisPublisher:
    def __init__(self, redis_client: Any, channel: str = "marketcore.ingest") -> None:
        self._redis_client = redis_client
        self._channel = channel

    @property
    def channel(self) -> str:
        return self._channel

    async def publish(self, event: BaseModel | Mapping[str, Any]) -> int:
        payload = encode_event_for_publication(event)
        return int(await self._redis_client.publish(self._channel, payload))
