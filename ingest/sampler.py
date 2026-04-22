from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ingest.models import CanonicalTopOfBookSnapshot


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _total_microseconds(value: timedelta) -> int:
    return ((value.days * 24 * 60 * 60) + value.seconds) * 1_000_000 + value.microseconds


def _align_interval_boundary(timestamp: datetime, interval: timedelta, *, round_up: bool) -> datetime:
    normalized_timestamp = _require_utc_aware_datetime(timestamp)
    interval_microseconds = _total_microseconds(interval)
    elapsed_microseconds = _total_microseconds(normalized_timestamp - _EPOCH)
    remainder = elapsed_microseconds % interval_microseconds

    if remainder == 0:
        aligned_microseconds = elapsed_microseconds
    elif round_up:
        aligned_microseconds = elapsed_microseconds + (interval_microseconds - remainder)
    else:
        aligned_microseconds = elapsed_microseconds - remainder

    return _EPOCH + timedelta(microseconds=aligned_microseconds)


def _require_utc_aware_datetime(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return timestamp.astimezone(UTC)


def _snapshot_order_key(snapshot: CanonicalTopOfBookSnapshot) -> tuple[datetime, int]:
    return (_require_utc_aware_datetime(snapshot.event_time), snapshot.update_id)


@dataclass
class _SymbolState:
    latest_order_key: tuple[datetime, int] | None = None
    pending: deque[CanonicalTopOfBookSnapshot] = field(default_factory=deque)
    active_snapshot: CanonicalTopOfBookSnapshot | None = None


class TopOfBookSampler:
    def __init__(self, interval: timedelta = timedelta(milliseconds=250)) -> None:
        if interval <= timedelta(0):
            raise ValueError("interval must be positive")
        self._interval = interval
        self._states_by_symbol: dict[str, _SymbolState] = {}
        self._next_flush_at: datetime | None = None

    def observe(self, snapshot: CanonicalTopOfBookSnapshot) -> None:
        event_time = _require_utc_aware_datetime(snapshot.event_time)
        _require_utc_aware_datetime(snapshot.ingested_at)
        symbol = snapshot.symbol.lower()
        snapshot = snapshot.model_copy(update={"symbol": symbol, "event_time": event_time})
        incoming_order_key = (event_time, snapshot.update_id)
        state = self._states_by_symbol.setdefault(symbol, _SymbolState())

        if state.latest_order_key is not None and incoming_order_key <= state.latest_order_key:
            return

        state.latest_order_key = incoming_order_key
        state.pending.append(snapshot)

        if self._next_flush_at is None:
            self._next_flush_at = _align_interval_boundary(
                event_time,
                self._interval,
                round_up=True,
            )

    def flush_due(self, now: datetime) -> list[CanonicalTopOfBookSnapshot]:
        normalized_now = _require_utc_aware_datetime(now)
        if self._next_flush_at is None:
            return []

        last_due_at = _align_interval_boundary(normalized_now, self._interval, round_up=False)
        if last_due_at < self._next_flush_at:
            return []

        emitted: list[CanonicalTopOfBookSnapshot] = []
        flush_at = self._next_flush_at
        while flush_at <= last_due_at:
            for symbol in sorted(self._states_by_symbol):
                state = self._states_by_symbol[symbol]
                while state.pending and state.pending[0].event_time <= flush_at:
                    state.active_snapshot = state.pending.popleft()

                if state.active_snapshot is not None:
                    emitted.append(state.active_snapshot.model_copy(update={"event_time": flush_at}))
            flush_at += self._interval

        self._next_flush_at = flush_at
        return emitted
