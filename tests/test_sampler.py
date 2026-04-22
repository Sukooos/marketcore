from datetime import UTC, datetime, timedelta

import pytest

from ingest.models import CanonicalTopOfBookSnapshot
from ingest.sampler import TopOfBookSampler


def make_snapshot(
    *,
    symbol: str,
    event_time: datetime,
    ingested_at: datetime,
    update_id: int,
    bid_price: str,
) -> CanonicalTopOfBookSnapshot:
    return CanonicalTopOfBookSnapshot(
        source="binance",
        event_type="book_ticker",
        symbol=symbol,
        event_time=event_time,
        ingested_at=ingested_at,
        raw_payload={"s": symbol.upper(), "u": update_id},
        raw_payload_hash=f"hash-{symbol}-{update_id}",
        update_id=update_id,
        bid_price=bid_price,
        bid_quantity="1.0",
        ask_price="63000.20",
        ask_quantity="0.8",
    )


def test_sampler_emits_latest_snapshot_for_each_due_interval() -> None:
    sampler = TopOfBookSampler(interval=timedelta(milliseconds=250))
    base_time = datetime(2026, 4, 22, 3, 0, 0, tzinfo=UTC)

    sampler.observe(
        make_snapshot(
            symbol="BTCUSDT",
            event_time=base_time + timedelta(milliseconds=100),
            ingested_at=base_time + timedelta(milliseconds=101),
            update_id=11,
            bid_price="62999.90",
        )
    )
    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=240),
            ingested_at=base_time + timedelta(milliseconds=241),
            update_id=12,
            bid_price="63000.00",
        )
    )
    sampler.observe(
        make_snapshot(
            symbol="ETHUSDT",
            event_time=base_time + timedelta(milliseconds=249),
            ingested_at=base_time + timedelta(milliseconds=249),
            update_id=21,
            bid_price="3200.10",
        )
    )

    first_flush = sampler.flush_due(base_time + timedelta(milliseconds=250))

    assert [snapshot.symbol for snapshot in first_flush] == ["btcusdt", "ethusdt"]
    assert [snapshot.update_id for snapshot in first_flush] == [12, 21]
    assert [snapshot.bid_price for snapshot in first_flush] == ["63000.00", "3200.10"]
    assert all(snapshot.event_time == base_time + timedelta(milliseconds=250) for snapshot in first_flush)
    assert all(snapshot.event_time.tzinfo is UTC for snapshot in first_flush)

    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=300),
            ingested_at=base_time + timedelta(milliseconds=301),
            update_id=13,
            bid_price="63000.05",
        )
    )

    second_flush = sampler.flush_due(base_time + timedelta(milliseconds=500))

    assert [snapshot.symbol for snapshot in second_flush] == ["btcusdt", "ethusdt"]
    assert [snapshot.update_id for snapshot in second_flush] == [13, 21]
    assert [snapshot.bid_price for snapshot in second_flush] == ["63000.05", "3200.10"]
    assert all(snapshot.event_time == base_time + timedelta(milliseconds=500) for snapshot in second_flush)


def test_sampler_does_not_backfill_earlier_bucket_with_future_state() -> None:
    sampler = TopOfBookSampler(interval=timedelta(milliseconds=250))
    base_time = datetime(2026, 4, 22, 3, 0, 0, tzinfo=UTC)

    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=240),
            ingested_at=base_time + timedelta(milliseconds=241),
            update_id=12,
            bid_price="63000.00",
        )
    )
    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=300),
            ingested_at=base_time + timedelta(milliseconds=301),
            update_id=13,
            bid_price="63000.05",
        )
    )

    delayed_flush = sampler.flush_due(base_time + timedelta(milliseconds=500))

    assert [snapshot.event_time for snapshot in delayed_flush] == [
        base_time + timedelta(milliseconds=250),
        base_time + timedelta(milliseconds=500),
    ]
    assert [snapshot.update_id for snapshot in delayed_flush] == [12, 13]
    assert [snapshot.bid_price for snapshot in delayed_flush] == ["63000.00", "63000.05"]


def test_sampler_ignores_stale_or_out_of_order_snapshots() -> None:
    sampler = TopOfBookSampler(interval=timedelta(milliseconds=250))
    base_time = datetime(2026, 4, 22, 3, 0, 0, tzinfo=UTC)

    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=240),
            ingested_at=base_time + timedelta(milliseconds=241),
            update_id=12,
            bid_price="63000.00",
        )
    )
    sampler.observe(
        make_snapshot(
            symbol="BTCUSDT",
            event_time=base_time + timedelta(milliseconds=200),
            ingested_at=base_time + timedelta(milliseconds=242),
            update_id=11,
            bid_price="62999.95",
        )
    )
    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=240),
            ingested_at=base_time + timedelta(milliseconds=243),
            update_id=10,
            bid_price="62999.97",
        )
    )
    sampler.observe(
        make_snapshot(
            symbol="btcusdt",
            event_time=base_time + timedelta(milliseconds=240),
            ingested_at=base_time + timedelta(milliseconds=244),
            update_id=13,
            bid_price="63000.02",
        )
    )

    flushed = sampler.flush_due(base_time + timedelta(milliseconds=250))

    assert [snapshot.symbol for snapshot in flushed] == ["btcusdt"]
    assert [snapshot.update_id for snapshot in flushed] == [13]
    assert [snapshot.bid_price for snapshot in flushed] == ["63000.02"]


def test_sampler_rejects_naive_datetimes() -> None:
    sampler = TopOfBookSampler(interval=timedelta(milliseconds=250))
    naive_time = datetime(2026, 4, 22, 3, 0, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        sampler.flush_due(naive_time)

    with pytest.raises(ValueError, match="timezone-aware"):
        sampler.observe(
            make_snapshot(
                symbol="btcusdt",
                event_time=datetime(2026, 4, 22, 3, 0, 0, 240_000, tzinfo=UTC),
                ingested_at=datetime(2026, 4, 22, 3, 0, 0, 1_000, tzinfo=UTC),
                update_id=12,
                bid_price="63000.00",
            ).model_copy(update={"event_time": naive_time})
        )

    aware_snapshot = make_snapshot(
        symbol="btcusdt",
        event_time=datetime(2026, 4, 22, 3, 0, 0, 240_000, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, 3, 0, 0, 241_000, tzinfo=UTC),
        update_id=12,
        bid_price="63000.00",
    )
    sampler.observe(aware_snapshot)

    with pytest.raises(ValueError, match="timezone-aware"):
        sampler.flush_due(naive_time)
