from backtest.replay import events_equal
import pytest


def test_events_equal_requires_exact_canonical_payload_equality() -> None:
    left = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "event_id": "trade:BTCUSDT:1",
        "price": "63000.10",
    }
    right = {
        "price": "63000.10",
        "event_id": "trade:BTCUSDT:1",
        "event_type": "trade",
        "symbol": "btcusdt",
    }

    assert events_equal(left, right) is True


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_events_equal_rejects_non_finite_numeric_values(value: float) -> None:
    payload = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "price": value,
    }

    with pytest.raises(ValueError, match="non-finite"):
        events_equal(payload, payload)


def test_events_equal_rejects_non_finite_numeric_values_in_nested_payload() -> None:
    payload = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "price": "63000.10",
        "metadata": {"levels": [1, float("nan")]},
    }

    with pytest.raises(ValueError, match="non-finite"):
        events_equal(payload, payload)


def test_events_equal_rejects_tuple_values() -> None:
    left = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "levels": (1, 2, 3),
    }
    right = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "levels": [1, 2, 3],
    }

    with pytest.raises(ValueError, match="non-JSON-native"):
        events_equal(left, right)
