from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from ingest.models import CanonicalTopOfBookSnapshot, CanonicalTrade


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("ascii")).hexdigest()


def _snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(payload)


def _parse_buyer_maker_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("buyer maker flag must be a boolean")


def _event_time_from_millis(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def normalize_trade(payload: dict[str, Any], ingested_at: datetime) -> CanonicalTrade:
    raw_payload = _snapshot_payload(payload)
    return CanonicalTrade(
        source="binance",
        event_type="trade",
        symbol=str(payload["s"]),
        event_time=_event_time_from_millis(int(payload["E"])),
        ingested_at=ingested_at,
        raw_payload=raw_payload,
        raw_payload_hash=_hash_payload(raw_payload),
        trade_id=int(payload["t"]),
        price=str(payload["p"]),
        quantity=str(payload["q"]),
        is_buyer_maker=_parse_buyer_maker_flag(payload["m"]),
    )


def normalize_book_ticker(
    payload: dict[str, Any], event_time: datetime, ingested_at: datetime
) -> CanonicalTopOfBookSnapshot:
    raw_payload = _snapshot_payload(payload)
    return CanonicalTopOfBookSnapshot(
        source="binance",
        event_type="book_ticker",
        symbol=str(payload["s"]),
        event_time=event_time,
        ingested_at=ingested_at,
        raw_payload=raw_payload,
        raw_payload_hash=_hash_payload(raw_payload),
        update_id=int(payload["u"]),
        bid_price=str(payload["b"]),
        bid_quantity=str(payload["B"]),
        ask_price=str(payload["a"]),
        ask_quantity=str(payload["A"]),
    )
