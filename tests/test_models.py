from ingest.config import Settings
from datetime import UTC, datetime

from ingest.models import CanonicalTrade


def test_settings_default_sampling_interval_ms() -> None:
    settings = Settings(
        binance_ws_url="wss://stream.binance.com:9443/ws",
        database_dsn="postgresql://postgres:postgres@localhost:5432/marketcore",
        redis_dsn="redis://localhost:6379/0",
    )

    assert settings.top_of_book_interval_ms == 250
    assert settings.symbols == ("btcusdt", "ethusdt", "solusdt")


def test_canonical_trade_requires_utc_aware_datetimes() -> None:
    event_time = datetime(2026, 4, 22, 3, 0, tzinfo=UTC)
    ingested_at = datetime(2026, 4, 22, 3, 0, 1, tzinfo=UTC)

    trade = CanonicalTrade(
        source="binance",
        event_type="trade",
        symbol="btcusdt",
        event_time=event_time,
        ingested_at=ingested_at,
        raw_payload={"e": "trade"},
        raw_payload_hash="abc123",
        trade_id=123456,
        price="63000.10",
        quantity="0.005",
        is_buyer_maker=True,
    )

    assert trade.event_time.tzinfo is UTC
    assert trade.ingested_at.tzinfo is UTC
    assert trade.symbol == "btcusdt"
