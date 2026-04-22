from __future__ import annotations

from datetime import UTC, datetime

from ingest.models import CanonicalTopOfBookSnapshot, CanonicalTrade
from ingest.storage import RAW_EVENTS_DDL, RAW_EVENTS_REPLAY_QUERY, serialize_event_row


def test_serialize_event_row_preserves_trade_identity_fields() -> None:
    event = CanonicalTrade(
        source="binance",
        event_type="trade",
        symbol="BTCUSDT",
        event_time=datetime(2026, 4, 22, 3, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, 3, 0, 1, tzinfo=UTC),
        raw_payload={"s": "BTCUSDT", "t": 123456, "p": "63000.10"},
        raw_payload_hash="abc123",
        trade_id=123456,
        price="63000.10",
        quantity="0.25",
        is_buyer_maker=False,
    )

    row = serialize_event_row(event)

    assert row["source"] == "binance"
    assert row["symbol"] == "btcusdt"
    assert row["event_type"] == "trade"
    assert row["event_time"] == datetime(2026, 4, 22, 3, 0, tzinfo=UTC)
    assert row["ingested_at"] == datetime(2026, 4, 22, 3, 0, 1, tzinfo=UTC)
    assert row["trade_id"] == 123456
    assert row["update_id"] is None
    assert row["raw_payload_hash"] == "abc123"
    assert "event_sequence" not in row
    assert row["payload"]["trade_id"] == 123456
    assert row["payload"]["raw_payload_hash"] == "abc123"
    assert row["payload"]["event_time"] == "2026-04-22T03:00:00Z"


def test_serialize_event_row_preserves_book_ticker_identity_fields() -> None:
    event = CanonicalTopOfBookSnapshot(
        source="binance",
        event_type="book_ticker",
        symbol="BTCUSDT",
        event_time=datetime(2026, 4, 22, 3, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, 3, 0, 0, 500000, tzinfo=UTC),
        raw_payload={"s": "BTCUSDT", "u": 987654, "b": "63000.00"},
        raw_payload_hash="def456",
        update_id=987654,
        bid_price="63000.00",
        bid_quantity="1.5",
        ask_price="63000.10",
        ask_quantity="2.5",
    )

    row = serialize_event_row(event)

    assert row["source"] == "binance"
    assert row["symbol"] == "btcusdt"
    assert row["event_type"] == "book_ticker"
    assert row["trade_id"] is None
    assert row["update_id"] == 987654
    assert row["raw_payload_hash"] == "def456"
    assert "event_sequence" not in row
    assert row["payload"]["update_id"] == 987654
    assert row["payload"]["raw_payload_hash"] == "def456"


def test_raw_events_ddl_disambiguates_same_identity_events_by_payload_hash() -> None:
    ddl = " ".join(RAW_EVENTS_DDL.split())

    assert "trade_id BIGINT NULL" in RAW_EVENTS_DDL
    assert "update_id BIGINT NULL" in RAW_EVENTS_DDL
    assert "raw_payload_hash TEXT NOT NULL" in RAW_EVENTS_DDL
    assert "PRIMARY KEY (source, symbol, event_type, event_time, raw_payload_hash)" in ddl
    assert "ingested_at" not in RAW_EVENTS_DDL.split("PRIMARY KEY", maxsplit=1)[1]
    assert "event_sequence BIGINT NOT NULL" not in RAW_EVENTS_DDL
    assert (
        "CREATE UNIQUE INDEX raw_events_trade_identity_idx ON raw_events "
        "(source, symbol, event_type, event_time, trade_id, raw_payload_hash) "
        "WHERE event_type = 'trade' AND trade_id IS NOT NULL;"
    ) in ddl
    assert (
        "CREATE UNIQUE INDEX raw_events_book_ticker_identity_idx ON raw_events "
        "(source, symbol, event_type, event_time, update_id, raw_payload_hash) "
        "WHERE event_type = 'book_ticker' AND update_id IS NOT NULL;"
    ) in ddl


def test_replay_query_requires_source_and_preserves_ingest_order_before_event_type() -> None:
    assert "WHERE source = $1" in RAW_EVENTS_REPLAY_QUERY
    assert "AND symbol = $2" in RAW_EVENTS_REPLAY_QUERY
    assert "AND event_time >= $3" in RAW_EVENTS_REPLAY_QUERY
    assert "AND event_time < $4" in RAW_EVENTS_REPLAY_QUERY
    assert "ORDER BY" in RAW_EVENTS_REPLAY_QUERY
    assert "event_time ASC" in RAW_EVENTS_REPLAY_QUERY
    assert "ingested_at ASC" in RAW_EVENTS_REPLAY_QUERY
    assert RAW_EVENTS_REPLAY_QUERY.index("ingested_at ASC") < RAW_EVENTS_REPLAY_QUERY.index("event_type ASC")
    assert "event_type ASC" in RAW_EVENTS_REPLAY_QUERY
    assert "trade_id ASC NULLS FIRST" in RAW_EVENTS_REPLAY_QUERY
    assert "update_id ASC NULLS FIRST" in RAW_EVENTS_REPLAY_QUERY
    assert "raw_payload_hash ASC" in RAW_EVENTS_REPLAY_QUERY


def test_same_canonical_event_with_different_ingested_at_keeps_same_identity() -> None:
    first_seen = CanonicalTrade(
        source="binance",
        event_type="trade",
        symbol="BTCUSDT",
        event_time=datetime(2026, 4, 22, 3, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, 3, 0, 1, tzinfo=UTC),
        raw_payload={"s": "BTCUSDT", "t": 123456, "p": "63000.10"},
        raw_payload_hash="abc123",
        trade_id=123456,
        price="63000.10",
        quantity="0.25",
        is_buyer_maker=False,
    )
    re_seen = first_seen.model_copy(
        update={"ingested_at": datetime(2026, 4, 22, 3, 0, 5, tzinfo=UTC)}
    )

    first_row = serialize_event_row(first_seen)
    re_seen_row = serialize_event_row(re_seen)

    first_identity = {
        key: first_row[key]
        for key in ("source", "symbol", "event_type", "event_time", "trade_id", "update_id", "raw_payload_hash")
    }
    re_seen_identity = {
        key: re_seen_row[key]
        for key in ("source", "symbol", "event_type", "event_time", "trade_id", "update_id", "raw_payload_hash")
    }

    assert first_identity == re_seen_identity
    assert first_row["ingested_at"] != re_seen_row["ingested_at"]


def test_same_book_ticker_event_with_different_ingested_at_keeps_same_identity() -> None:
    first_seen = CanonicalTopOfBookSnapshot(
        source="binance",
        event_type="book_ticker",
        symbol="BTCUSDT",
        event_time=datetime(2026, 4, 22, 3, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, 3, 0, 0, 500000, tzinfo=UTC),
        raw_payload={"s": "BTCUSDT", "u": 987654, "b": "63000.00"},
        raw_payload_hash="def456",
        update_id=987654,
        bid_price="63000.00",
        bid_quantity="1.5",
        ask_price="63000.10",
        ask_quantity="2.5",
    )
    re_seen = first_seen.model_copy(
        update={"ingested_at": datetime(2026, 4, 22, 3, 0, 2, tzinfo=UTC)}
    )

    first_row = serialize_event_row(first_seen)
    re_seen_row = serialize_event_row(re_seen)

    first_identity = {
        key: first_row[key]
        for key in ("source", "symbol", "event_type", "event_time", "trade_id", "update_id", "raw_payload_hash")
    }
    re_seen_identity = {
        key: re_seen_row[key]
        for key in ("source", "symbol", "event_type", "event_time", "trade_id", "update_id", "raw_payload_hash")
    }

    assert first_identity == re_seen_identity
    assert first_row["ingested_at"] != re_seen_row["ingested_at"]
