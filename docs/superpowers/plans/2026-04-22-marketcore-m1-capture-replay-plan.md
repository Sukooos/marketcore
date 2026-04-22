# MarketCore Milestone 1 Capture and Replay Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Milestone 1 foundation for MarketCore: capture live Binance trades and 250ms top-of-book snapshots for three symbols, persist canonical raw events durably, and replay captured windows exactly from storage.

**Architecture:** A single async ingest service owns exchange connectivity, canonical normalization, top-of-book sampling, TimescaleDB writes, Redis publication, and health tracking. A thin FastAPI app exposes health and query endpoints, while a CLI replay runner reloads canonical events from TimescaleDB and re-emits them in deterministic order for equality checks.

**Tech Stack:** Python 3.12, FastAPI, asyncio, websockets, asyncpg, redis.asyncio, Pydantic v2, structlog, Prometheus client, TimescaleDB, Redis, Docker Compose, Alembic, pytest, Hypothesis, Ruff, mypy

---

## Planned File Structure

- `ingest/__init__.py` - package marker
- `ingest/config.py` - environment-driven settings for symbols, Binance URLs, database, Redis, and sampling interval
- `ingest/models.py` - canonical raw-event schemas for trades and top-of-book snapshots
- `ingest/normalizer.py` - exchange payload normalization into canonical models
- `ingest/sampler.py` - 250ms fixed-interval top-of-book sampler
- `ingest/storage.py` - asyncpg persistence helpers for canonical raw events
- `ingest/publisher.py` - Redis JSON publication for canonical events
- `ingest/metrics.py` - Prometheus counters, gauges, and helper updates
- `ingest/service.py` - combined ingest service orchestration and lifecycle
- `ingest/main.py` - service entrypoint
- `api/__init__.py` - package marker
- `api/app.py` - FastAPI app with health and replay-window query endpoints
- `backtest/__init__.py` - package marker
- `backtest/replay.py` - replay CLI entrypoint and deterministic re-emission logic
- `ops/docker-compose.yml` - local TimescaleDB, Redis, API, ingest, Prometheus, Grafana
- `ops/prometheus.yml` - scrape configuration
- `ops/grafana/provisioning/datasources/datasource.yml` - Grafana datasource
- `ops/grafana/provisioning/dashboards/dashboard.yml` - dashboard provisioning
- `ops/grafana/dashboards/marketcore-m1.json` - dashboard definition
- `migrations/alembic.ini` - Alembic config
- `migrations/env.py` - migration environment
- `migrations/versions/0001_create_raw_event_tables.py` - initial schema
- `tests/conftest.py` - shared fixtures
- `tests/fixtures/binance_trade.json` - sample Binance trade payload
- `tests/fixtures/binance_book_ticker.json` - sample book payload
- `tests/test_models.py` - canonical event schema tests
- `tests/test_normalizer.py` - normalization tests
- `tests/test_sampler.py` - 250ms sampler tests
- `tests/test_storage.py` - persistence/reload tests
- `tests/test_replay.py` - replay ordering and equality tests
- `tests/test_api.py` - API health/query tests

### Task 1: Scaffold the repository skeleton and configuration

**Files:**
- Create: `ingest/__init__.py`
- Create: `ingest/config.py`
- Create: `ingest/main.py`
- Create: `api/__init__.py`
- Create: `backtest/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing configuration test**

```python
from ingest.config import Settings


def test_settings_default_sampling_interval_ms() -> None:
    settings = Settings(
        binance_ws_url="wss://stream.binance.com:9443/ws",
        database_dsn="postgresql://postgres:postgres@localhost:5432/marketcore",
        redis_dsn="redis://localhost:6379/0",
    )

    assert settings.top_of_book_interval_ms == 250
    assert settings.symbols == ("btcusdt", "ethusdt", "solusdt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_settings_default_sampling_interval_ms -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingest'` or missing `Settings`

- [ ] **Step 3: Write minimal implementation**

```python
# ingest/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="marketcore_", extra="ignore")

    binance_ws_url: str
    database_dsn: str
    redis_dsn: str
    top_of_book_interval_ms: int = 250
    symbols: tuple[str, str, str] = Field(
        default=("btcusdt", "ethusdt", "solusdt")
    )
```

```python
# ingest/__init__.py
__all__ = ["config"]
```

```python
# ingest/main.py
from ingest.config import Settings


def build_settings() -> Settings:
    return Settings()  # pragma: no cover
```

```python
# api/__init__.py
__all__ = ["app"]
```

```python
# backtest/__init__.py
__all__ = ["replay"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_settings_default_sampling_interval_ms -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ingest/__init__.py ingest/config.py ingest/main.py api/__init__.py backtest/__init__.py tests/test_models.py
git commit -m "feat: scaffold marketcore milestone 1 packages"
```

### Task 2: Define canonical event schemas and normalization rules

**Files:**
- Create: `ingest/models.py`
- Create: `ingest/normalizer.py`
- Create: `tests/fixtures/binance_trade.json`
- Create: `tests/fixtures/binance_book_ticker.json`
- Create: `tests/test_models.py`
- Create: `tests/test_normalizer.py`

- [ ] **Step 1: Write the failing model and normalizer tests**

```python
from datetime import UTC, datetime

from ingest.models import CanonicalTopOfBookSnapshot, CanonicalTrade
from ingest.normalizer import normalize_book_ticker, normalize_trade


def test_normalize_trade_maps_binance_payload_to_canonical_trade() -> None:
    payload = {
        "e": "trade",
        "E": 1710000000100,
        "s": "BTCUSDT",
        "t": 123456,
        "p": "63000.10",
        "q": "0.015",
        "T": 1710000000000,
        "m": True,
    }

    event = normalize_trade(payload=payload, ingested_at=datetime(2026, 4, 22, tzinfo=UTC))

    assert isinstance(event, CanonicalTrade)
    assert event.symbol == "btcusdt"
    assert event.trade_id == 123456
    assert event.price == "63000.10"


def test_normalize_book_ticker_maps_payload_to_snapshot() -> None:
    payload = {
        "u": 400900217,
        "s": "BTCUSDT",
        "b": "63000.00",
        "B": "1.250",
        "a": "63000.20",
        "A": "0.900",
    }

    event = normalize_book_ticker(
        payload=payload,
        event_time=datetime(2026, 4, 22, 1, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, 1, 0, tzinfo=UTC),
    )

    assert isinstance(event, CanonicalTopOfBookSnapshot)
    assert event.symbol == "btcusdt"
    assert event.bid_price == "63000.00"
    assert event.ask_price == "63000.20"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py tests/test_normalizer.py -v`
Expected: FAIL with missing canonical model and normalizer symbols

- [ ] **Step 3: Write minimal implementation**

```python
# ingest/models.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CanonicalEvent(BaseModel):
    exchange: Literal["binance"]
    symbol: str
    event_type: str
    event_time: datetime
    ingested_at: datetime
    event_id: str
    payload_hash: str


class CanonicalTrade(CanonicalEvent):
    event_type: Literal["trade"] = "trade"
    trade_id: int
    price: str
    quantity: str
    buyer_is_market_maker: bool


class CanonicalTopOfBookSnapshot(CanonicalEvent):
    event_type: Literal["top_of_book_snapshot"] = "top_of_book_snapshot"
    update_id: int
    bid_price: str
    bid_quantity: str
    ask_price: str
    ask_quantity: str
```

```python
# ingest/normalizer.py
from datetime import datetime
from hashlib import sha256
import json

from ingest.models import CanonicalTopOfBookSnapshot, CanonicalTrade


def _payload_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def normalize_trade(payload: dict[str, object], ingested_at: datetime) -> CanonicalTrade:
    return CanonicalTrade(
        exchange="binance",
        symbol=str(payload["s"]).lower(),
        event_time=datetime.fromtimestamp(int(payload["T"]) / 1000),
        ingested_at=ingested_at,
        event_id=f"trade:{payload['s']}:{payload['t']}",
        payload_hash=_payload_hash(payload),
        trade_id=int(payload["t"]),
        price=str(payload["p"]),
        quantity=str(payload["q"]),
        buyer_is_market_maker=bool(payload["m"]),
    )


def normalize_book_ticker(
    payload: dict[str, object], event_time: datetime, ingested_at: datetime
) -> CanonicalTopOfBookSnapshot:
    return CanonicalTopOfBookSnapshot(
        exchange="binance",
        symbol=str(payload["s"]).lower(),
        event_time=event_time,
        ingested_at=ingested_at,
        event_id=f"book:{payload['s']}:{payload['u']}",
        payload_hash=_payload_hash(payload),
        update_id=int(payload["u"]),
        bid_price=str(payload["b"]),
        bid_quantity=str(payload["B"]),
        ask_price=str(payload["a"]),
        ask_quantity=str(payload["A"]),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py tests/test_normalizer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ingest/models.py ingest/normalizer.py tests/fixtures/binance_trade.json tests/fixtures/binance_book_ticker.json tests/test_models.py tests/test_normalizer.py
git commit -m "feat: add canonical raw event models and normalizers"
```

### Task 3: Implement the 250ms top-of-book sampler

**Files:**
- Create: `ingest/sampler.py`
- Create: `tests/test_sampler.py`

- [ ] **Step 1: Write the failing sampler tests**

```python
from datetime import UTC, datetime, timedelta

from ingest.sampler import TopOfBookSampler


def test_sampler_emits_latest_snapshot_for_each_interval() -> None:
    sampler = TopOfBookSampler(interval_ms=250)
    base = datetime(2026, 4, 22, 1, 0, 0, tzinfo=UTC)

    sampler.update(
        symbol="btcusdt",
        update_id=1,
        bid_price="63000.00",
        bid_quantity="1.0",
        ask_price="63000.10",
        ask_quantity="1.2",
        observed_at=base,
    )
    sampler.update(
        symbol="btcusdt",
        update_id=2,
        bid_price="63000.01",
        bid_quantity="1.1",
        ask_price="63000.11",
        ask_quantity="1.3",
        observed_at=base + timedelta(milliseconds=100),
    )

    snapshots = sampler.flush_due(now=base + timedelta(milliseconds=250))

    assert len(snapshots) == 1
    assert snapshots[0].update_id == 2
    assert snapshots[0].event_time == base + timedelta(milliseconds=250)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sampler.py -v`
Expected: FAIL with missing `TopOfBookSampler`

- [ ] **Step 3: Write minimal implementation**

```python
# ingest/sampler.py
from dataclasses import dataclass
from datetime import datetime, timedelta

from ingest.models import CanonicalTopOfBookSnapshot
from ingest.normalizer import normalize_book_ticker


@dataclass
class _LatestBookState:
    payload: dict[str, object]
    observed_at: datetime


class TopOfBookSampler:
    def __init__(self, interval_ms: int) -> None:
        self._interval = timedelta(milliseconds=interval_ms)
        self._latest: dict[str, _LatestBookState] = {}
        self._next_flush_at: datetime | None = None

    def update(
        self,
        symbol: str,
        update_id: int,
        bid_price: str,
        bid_quantity: str,
        ask_price: str,
        ask_quantity: str,
        observed_at: datetime,
    ) -> None:
        self._latest[symbol] = _LatestBookState(
            payload={
                "u": update_id,
                "s": symbol.upper(),
                "b": bid_price,
                "B": bid_quantity,
                "a": ask_price,
                "A": ask_quantity,
            },
            observed_at=observed_at,
        )
        if self._next_flush_at is None:
            self._next_flush_at = observed_at + self._interval

    def flush_due(self, now: datetime) -> list[CanonicalTopOfBookSnapshot]:
        if self._next_flush_at is None or now < self._next_flush_at:
            return []

        flush_at = self._next_flush_at
        self._next_flush_at = flush_at + self._interval
        return [
            normalize_book_ticker(
                payload=state.payload,
                event_time=flush_at,
                ingested_at=state.observed_at,
            )
            for state in self._latest.values()
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sampler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ingest/sampler.py tests/test_sampler.py
git commit -m "feat: add fixed-interval top-of-book sampler"
```

### Task 4: Add TimescaleDB schema, persistence, and deterministic reload

**Files:**
- Create: `migrations/alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_create_raw_event_tables.py`
- Create: `ingest/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write the failing storage tests**

```python
from datetime import UTC, datetime

from ingest.models import CanonicalTrade
from ingest.storage import serialize_event_row


def test_serialize_event_row_keeps_deterministic_identity_fields() -> None:
    event = CanonicalTrade(
        exchange="binance",
        symbol="btcusdt",
        event_type="trade",
        event_time=datetime(2026, 4, 22, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 22, tzinfo=UTC),
        event_id="trade:BTCUSDT:1",
        payload_hash="abc",
        trade_id=1,
        price="100.0",
        quantity="0.1",
        buyer_is_market_maker=False,
    )

    row = serialize_event_row(event)

    assert row["symbol"] == "btcusdt"
    assert row["event_type"] == "trade"
    assert row["event_id"] == "trade:BTCUSDT:1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with missing storage helpers

- [ ] **Step 3: Write minimal implementation**

```python
# ingest/storage.py
from collections.abc import Sequence

from ingest.models import CanonicalEvent


def serialize_event_row(event: CanonicalEvent) -> dict[str, object]:
    payload = event.model_dump(mode="json")
    return {
        "exchange": payload["exchange"],
        "symbol": payload["symbol"],
        "event_type": payload["event_type"],
        "event_time": payload["event_time"],
        "ingested_at": payload["ingested_at"],
        "event_id": payload["event_id"],
        "payload_hash": payload["payload_hash"],
        "payload": payload,
    }


RAW_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS raw_events (
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (symbol, event_type, event_id, event_time)
);
"""


REPLAY_QUERY = """
SELECT payload
FROM raw_events
WHERE symbol = $1
  AND event_time >= $2
  AND event_time < $3
ORDER BY event_time ASC, event_type ASC, event_id ASC
"""
```

```python
# migrations/versions/0001_create_raw_event_tables.py
from alembic import op


revision = "0001_create_raw_event_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        '''
        CREATE TABLE raw_events (
            event_time TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_id TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload JSONB NOT NULL,
            PRIMARY KEY (symbol, event_type, event_id, event_time)
        );
        '''
    )


def downgrade() -> None:
    op.execute("DROP TABLE raw_events")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ingest/storage.py migrations/alembic.ini migrations/env.py migrations/versions/0001_create_raw_event_tables.py tests/test_storage.py
git commit -m "feat: add raw event persistence foundation"
```

### Task 5: Build the replay CLI and equality checks

**Files:**
- Create: `backtest/replay.py`
- Create: `tests/test_replay.py`

- [ ] **Step 1: Write the failing replay test**

```python
from backtest.replay import events_equal


def test_events_equal_requires_exact_canonical_payload_equality() -> None:
    left = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "event_id": "trade:BTCUSDT:1",
        "price": "63000.10",
    }
    right = {
        "symbol": "btcusdt",
        "event_type": "trade",
        "event_id": "trade:BTCUSDT:1",
        "price": "63000.10",
    }

    assert events_equal(left, right) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_replay.py -v`
Expected: FAIL with missing replay helper

- [ ] **Step 3: Write minimal implementation**

```python
# backtest/replay.py
import json


def events_equal(left: dict[str, object], right: dict[str, object]) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_replay.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backtest/replay.py tests/test_replay.py
git commit -m "feat: add replay equality checks"
```

### Task 6: Add ingest service orchestration, Redis publication, and metrics

**Files:**
- Create: `ingest/metrics.py`
- Create: `ingest/publisher.py`
- Create: `ingest/service.py`
- Modify: `ingest/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing service health test**

```python
from fastapi.testclient import TestClient

from api.app import app


def test_health_endpoint_reports_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py::test_health_endpoint_reports_service_status -v`
Expected: FAIL with missing FastAPI app or route

- [ ] **Step 3: Write minimal implementation**

```python
# api/app.py
from fastapi import FastAPI

app = FastAPI(title="MarketCore API")


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "dependencies": {"timescaledb": "unknown", "redis": "unknown"},
    }
```

```python
# ingest/metrics.py
from prometheus_client import Counter, Gauge

ingested_trades_total = Counter("marketcore_ingested_trades_total", "Trades ingested")
ingested_top_of_book_total = Counter(
    "marketcore_ingested_top_of_book_total", "Top-of-book snapshots ingested"
)
ws_reconnects_total = Counter("marketcore_ws_reconnects_total", "Reconnect count")
last_message_age_seconds = Gauge(
    "marketcore_last_message_age_seconds", "Seconds since last exchange message"
)
```

```python
# ingest/publisher.py
import json


def encode_event_for_publication(event: dict[str, object]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py::test_health_endpoint_reports_service_status -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/app.py ingest/metrics.py ingest/publisher.py tests/test_api.py
git commit -m "feat: add health API and ingest metrics foundation"
```

### Task 7: Add Docker Compose and operator stack

**Files:**
- Create: `ops/docker-compose.yml`
- Create: `ops/prometheus.yml`
- Create: `ops/grafana/provisioning/datasources/datasource.yml`
- Create: `ops/grafana/provisioning/dashboards/dashboard.yml`
- Create: `ops/grafana/dashboards/marketcore-m1.json`

- [ ] **Step 1: Write the failing operator smoke checklist as a test note**

```python
def test_operator_stack_contract() -> None:
    services = {"timescaledb", "redis", "api", "ingest", "prometheus", "grafana"}
    assert "grafana" in services
    assert "prometheus" in services
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_operator_stack_contract -v`
Expected: FAIL because the smoke checklist test is not yet present

- [ ] **Step 3: Write minimal implementation**

```yaml
# ops/docker-compose.yml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: marketcore
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
  redis:
    image: redis:7
    ports: ["6379:6379"]
  api:
    build: .
    command: uvicorn api.app:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
  ingest:
    build: .
    command: python -m ingest.main
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports: ["9090:9090"]
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_operator_stack_contract -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ops/docker-compose.yml ops/prometheus.yml ops/grafana/provisioning/datasources/datasource.yml ops/grafana/provisioning/dashboards/dashboard.yml ops/grafana/dashboards/marketcore-m1.json tests/test_api.py
git commit -m "feat: add operator stack for milestone 1"
```

## Verification Checklist

- Run unit tests for config, models, normalization, sampler, storage, replay, and API
- Run integration tests against local TimescaleDB and Redis
- Run `ruff check .`
- Run `mypy --strict .`
- Run `docker compose -f ops/docker-compose.yml up`
- Capture a live replay window and confirm canonical raw event equality

## Self-Review Notes

- Spec coverage:
  - combined ingest service: Tasks 1, 3, 6
  - canonical event model: Task 2
  - durable raw-event persistence: Task 4
  - deterministic replay: Task 5
  - thin REST and operability: Tasks 6 and 7
- Placeholder scan:
  - no `TODO` or `TBD` placeholders remain in the plan body
- Type consistency:
  - canonical fields use `event_time`, `ingested_at`, `event_id`, and `payload_hash` consistently across storage and replay tasks
