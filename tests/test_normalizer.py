import json
from typing import Any, cast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ingest.models import CanonicalTopOfBookSnapshot, CanonicalTrade
from ingest.normalizer import normalize_book_ticker, normalize_trade


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / name).read_text(encoding="ascii")))


def test_normalize_trade_returns_canonical_trade() -> None:
    payload = load_fixture("binance_trade.json")
    ingested_at = datetime(2026, 4, 22, 3, 5, tzinfo=UTC)

    event = normalize_trade(payload, ingested_at)

    assert isinstance(event, CanonicalTrade)
    assert event.source == "binance"
    assert event.event_type == "trade"
    assert event.symbol == "btcusdt"
    assert event.trade_id == 123456
    assert event.price == "63000.10"
    assert event.quantity == "0.005"
    assert event.is_buyer_maker is True
    assert event.event_time == datetime(2026, 4, 22, 3, 4, 5, 678000, tzinfo=UTC)
    assert event.ingested_at == ingested_at
    assert event.raw_payload == payload
    assert (
        event.raw_payload_hash
        == "0e5b2f9f294745fd875564ef707b80290df9f3b8ba16afe4e13824a590b6b25e"
    )


def test_normalize_trade_snapshots_raw_payload() -> None:
    payload = load_fixture("binance_trade.json")
    payload["meta"] = {"route": "alpha"}
    ingested_at = datetime(2026, 4, 22, 3, 5, tzinfo=UTC)

    event = normalize_trade(payload, ingested_at)
    payload["meta"]["route"] = "beta"

    assert event.raw_payload["meta"]["route"] == "alpha"
    assert (
        event.raw_payload_hash
        == "38ff4fd23252c8aa94fe9a80023cb860c81f1d57e1678829afe1c914aa81bda0"
    )


def test_normalize_trade_rejects_non_boolean_buyer_maker_flag() -> None:
    payload = load_fixture("binance_trade.json")
    payload["m"] = "true"
    ingested_at = datetime(2026, 4, 22, 3, 5, tzinfo=UTC)

    with pytest.raises(ValueError, match="buyer maker flag"):
        normalize_trade(payload, ingested_at)


def test_normalize_book_ticker_returns_top_of_book_snapshot() -> None:
    payload = load_fixture("binance_book_ticker.json")
    event_time = datetime(2026, 4, 22, 3, 6, 7, 890000, tzinfo=UTC)
    ingested_at = datetime(2026, 4, 22, 3, 6, 8, tzinfo=UTC)

    event = normalize_book_ticker(payload, event_time, ingested_at)

    assert isinstance(event, CanonicalTopOfBookSnapshot)
    assert event.source == "binance"
    assert event.event_type == "book_ticker"
    assert event.symbol == "btcusdt"
    assert event.update_id == 987654321
    assert event.bid_price == "62999.90"
    assert event.bid_quantity == "1.250"
    assert event.ask_price == "63000.20"
    assert event.ask_quantity == "0.875"
    assert event.event_time == event_time
    assert event.ingested_at == ingested_at
    assert event.raw_payload == payload
    assert (
        event.raw_payload_hash
        == "48b486c7d20ea7f14da502299789a3c90226f2b5adbdaa74b289682aad14e2c2"
    )
