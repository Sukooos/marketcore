from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CanonicalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    event_type: str
    symbol: str
    event_time: datetime
    ingested_at: datetime
    raw_payload: dict[str, Any]
    raw_payload_hash: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.lower()

    @field_validator("event_time", "ingested_at")
    @classmethod
    def require_utc_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return value.astimezone(UTC)


class CanonicalTrade(CanonicalEvent):
    trade_id: int
    price: str
    quantity: str
    is_buyer_maker: bool


class CanonicalTopOfBookSnapshot(CanonicalEvent):
    update_id: int
    bid_price: str
    bid_quantity: str
    ask_price: str
    ask_quantity: str
