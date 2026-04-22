from __future__ import annotations

from typing import Any

from ingest.models import CanonicalEvent

RAW_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS raw_events (
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    trade_id BIGINT NULL,
    update_id BIGINT NULL,
    raw_payload_hash TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (source, symbol, event_type, event_time, raw_payload_hash)
);
CREATE UNIQUE INDEX raw_events_trade_identity_idx ON raw_events
    (source, symbol, event_type, event_time, trade_id, raw_payload_hash)
    WHERE event_type = 'trade' AND trade_id IS NOT NULL;
CREATE UNIQUE INDEX raw_events_book_ticker_identity_idx ON raw_events
    (source, symbol, event_type, event_time, update_id, raw_payload_hash)
    WHERE event_type = 'book_ticker' AND update_id IS NOT NULL;
"""

RAW_EVENTS_REPLAY_QUERY = """
SELECT payload
FROM raw_events
WHERE source = $1
  AND symbol = $2
  AND event_time >= $3
  AND event_time < $4
ORDER BY
    event_time ASC,
    ingested_at ASC,
    event_type ASC,
    trade_id ASC NULLS FIRST,
    update_id ASC NULLS FIRST,
    raw_payload_hash ASC
"""


def serialize_event_row(event: CanonicalEvent) -> dict[str, Any]:
    payload = event.model_dump(mode="json")
    row: dict[str, Any] = {
        "event_time": event.event_time,
        "ingested_at": event.ingested_at,
        "source": event.source,
        "symbol": event.symbol,
        "event_type": event.event_type,
        "trade_id": getattr(event, "trade_id", None),
        "update_id": getattr(event, "update_id", None),
        "raw_payload_hash": event.raw_payload_hash,
        "payload": payload,
    }
    return row
