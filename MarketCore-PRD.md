# MarketCore — Real-Time Trading Infrastructure & Research Platform

Portfolio project combining live market data infrastructure (Tier 2 #1) with historical data pipeline and feature store (Tier 2 #2) into a single, coherent system.

## 1. Overview

MarketCore ingests real-time market data from Binance, computes technical features, generates trading signals, and serves them over REST/gRPC. The same feature engine runs against historical data for backtesting, guaranteeing research/live parity.

Target users (of this project's narrative): hiring managers for Quant Developer, Trading Systems Engineer, and Fintech Backend roles.

## 2. Goals

- Ingest trades and L2 order book from Binance continuously without manual intervention.
- Compute technical features (RSI, MACD, Bollinger, order book imbalance) in both streaming and batch modes using shared logic.
- Generate rule-based signals and serve them via REST + gRPC + WebSocket.
- Provide a backtester that replays history through the same signal engine.
- Expose production-grade observability (metrics, logs, dashboards).

## 3. Non-Goals (v1)

- Live order execution or auto-trading.
- Multi-exchange aggregation (single exchange for v1).
- ML model training and inference.
- User authentication, multi-tenancy, billing.
- Kubernetes. A single VPS with Docker Compose is sufficient and demonstrates pragmatism.
- Tick-level historical data purchase. Use Binance's free historical REST endpoints.

## 4. Success Criteria

**Technical**
- Runs 7+ days continuously, 5 symbols, zero data gaps (verified by order book sequence numbers).
- End-to-end latency p99 < 500ms from exchange timestamp to signal published.
- Backtester produces bit-identical signals vs. live engine for replayed historical windows (parity test passes).
- All services recover automatically from: WebSocket disconnect, database restart, Redis restart.
- CI green on every push; all services start from `docker compose up`.

**Portfolio**
- README contains architecture diagram, decision log, 60-second demo video, actual performance numbers.
- Deployed live at a public URL with Grafana dashboard viewable (read-only).
- Documented interview-ready story: problem → design choices → tradeoffs → results.

## 5. Architecture

```
┌──────────────┐   WebSocket    ┌─────────────┐     ┌──────────────┐
│  Binance WS  │ ─────────────► │  Ingestion  │ ──► │  TimescaleDB │
└──────────────┘                │   Service   │     │  (hypertable)│
                                └──────┬──────┘     └──────┬───────┘
                                       │                   │
                                       ▼                   │
                                 ┌──────────┐              │
                                 │  Redis   │              │
                                 │ (stream  │              │
                                 │ + cache) │              │
                                 └────┬─────┘              │
                                      │                    │
                   ┌──────────────────┴──────┐             │
                   ▼                         ▼             │
           ┌──────────────┐          ┌──────────────┐      │
           │ Stream       │          │ Batch        │ ◄────┘
           │ Driver       │          │ Driver       │
           └──────┬───────┘          └──────┬───────┘
                  │                         │
                  └──────────┬──────────────┘
                             ▼
                    ┌─────────────────┐
                    │  Feature Engine │ ◄── shared library
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Signal Service │
                    └────────┬────────┘
                             │
               ┌─────────────┼──────────────┐
               ▼             ▼              ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │  REST    │  │  gRPC    │  │  WS      │
         │  API     │  │  Stream  │  │  Stream  │
         └──────────┘  └──────────┘  └──────────┘
```

### Core design decision: one feature engine, two drivers

The single most important architectural choice. The feature engine is a pure library with this contract:

```python
class FeatureEngine:
    def compute(self, window: Sequence[Bar]) -> dict[str, float]: ...
```

Two drivers call it:
- `StreamDriver` consumes from Redis streams, maintains bounded sliding windows in memory, emits features on each tick.
- `BatchDriver` scans TimescaleDB over a time range, emits features in chronological order.

This guarantees backtest-live parity and avoids the classic trap where research logic drifts from production logic. A dedicated parity test asserts identical output given identical input.

## 6. Modules

### 6.1 Ingestion Service (`ingest/`)
Async Python, one process per exchange.

Responsibilities:
- Maintain WebSocket connections for trade and depth streams.
- Validate order book sequence numbers; on gap, fetch REST snapshot and resume.
- Batch writes to TimescaleDB (500ms flush window, `COPY` for efficiency).
- Push latest order book to Redis (`ob:{exchange}:{symbol}`, TTL 5s).
- Publish raw events to Redis streams (`stream:trades`, `stream:depth`).

Failure handling:
- Exponential backoff reconnect (1s, 2s, 4s, ..., max 60s).
- Bounded in-memory buffer (10k events) during DB outage; drop-oldest policy with metric.
- Health endpoint reflects WS connection state, last-message age.

Stack: `websockets`, `asyncpg`, `redis.asyncio`, `pydantic`, `structlog`.

### 6.2 Historical ETL (`etl/`)
Batch CLI. Fetches OHLCV (1m, 5m, 1h) via Binance REST, upserts into TimescaleDB. Idempotent on `(exchange, symbol, interval, ts)`.

Stack: `httpx`, `asyncpg`.

### 6.3 Feature Engine (`features/`)
Pure library. No I/O, no state beyond function args. Features v1:
- RSI(14)
- MACD(12, 26, 9)
- Bollinger Bands(20, 2)
- Order book imbalance (top-N levels)

All feature implementations have property-based tests against reference values computed with `pandas-ta` or `talib` as oracle.

### 6.4 Signal Service (`signal/`)
Async service consuming feature events. Signals v1:
- MA(50)/MA(200) crossover on 1m close.
- Order book imbalance threshold (|imbalance| > 0.7 persisted for N seconds).

Writes to `signals` hypertable, publishes to Redis pub/sub channel `signals:{symbol}`.

### 6.5 API Layer (`api/`)
FastAPI service. Note on framework choice: Flask was considered (matches existing stack preference), but FastAPI is chosen here because the API needs native async (it consumes from Redis pub/sub for WS streaming), and integrates cleanly with gRPC async servicers. Flask would force sync/async bridging with no practical upside.

Endpoints:
- `GET /health` — liveness + dependency checks.
- `GET /v1/snapshot/{symbol}` — latest order book + last trade.
- `GET /v1/features/{symbol}?from=&to=&names=` — historical features.
- `GET /v1/signals/{symbol}?from=&to=` — historical signals.
- `WS /v1/ws/signals?symbols=` — live signal stream.
- gRPC `StreamSignals(SignalRequest) returns (stream Signal)` — same live stream for low-latency clients.

Auth: API key via `X-API-Key` header, validated against env-configured set. Rate limiting via Redis token bucket (100 req/min default).

### 6.6 Backtester (`backtest/`)
CLI tool. Inputs: symbol, date range, signal config. Outputs: HTML report with equity curve, PnL, Sharpe, max drawdown, trade log CSV.

Uses `BatchDriver` → `FeatureEngine` → `SignalService` (signal logic extracted as pure function). Custom implementation (not `vectorbt`) to demonstrate understanding; vectorbt could be added as v2.

### 6.7 Observability (`ops/`)
- Prometheus metrics on `/metrics` for every service.
- Key metrics: `messages_ingested_total`, `ingest_lag_seconds`, `ws_reconnects_total`, `feature_compute_duration_seconds`, `signals_emitted_total`, `api_request_duration_seconds`.
- Grafana dashboard JSON committed to repo, auto-provisioned.
- Structured JSON logs via `structlog`; correlation IDs per request/event.

## 7. Data Model

```sql
CREATE TABLE trades (
    ts          TIMESTAMPTZ NOT NULL,
    exchange    TEXT        NOT NULL,
    symbol      TEXT        NOT NULL,
    price       NUMERIC     NOT NULL,
    qty         NUMERIC     NOT NULL,
    side        TEXT        NOT NULL,
    trade_id    BIGINT      NOT NULL,
    PRIMARY KEY (exchange, symbol, trade_id, ts)
);
SELECT create_hypertable('trades', 'ts');
CREATE INDEX ON trades (exchange, symbol, ts DESC);

CREATE TABLE ohlcv (
    ts       TIMESTAMPTZ NOT NULL,
    exchange TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    interval TEXT NOT NULL,
    open  NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC,
    volume NUMERIC,
    PRIMARY KEY (exchange, symbol, interval, ts)
);
SELECT create_hypertable('ohlcv', 'ts');

CREATE TABLE features (
    ts       TIMESTAMPTZ NOT NULL,
    exchange TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    name     TEXT NOT NULL,
    value    DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (exchange, symbol, name, ts)
);
SELECT create_hypertable('features', 'ts');

CREATE TABLE signals (
    ts       TIMESTAMPTZ NOT NULL,
    exchange TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    signal   TEXT NOT NULL,
    strength DOUBLE PRECISION,
    metadata JSONB,
    PRIMARY KEY (exchange, symbol, signal, ts)
);
SELECT create_hypertable('signals', 'ts');
```

TimescaleDB continuous aggregates generate 1m/5m/1h OHLCV from `trades` automatically, removing the need for a separate aggregation job for live data.

## 8. Tech Stack Summary

| Concern | Choice | Reasoning |
|---|---|---|
| Language | Python 3.12 | Ecosystem, async maturity, quant/DS overlap |
| DB | TimescaleDB | Postgres-compatible, purpose-built for time-series |
| Cache / Pub-Sub | Redis 7 | Streams + pub/sub + key-value in one dep |
| API framework | FastAPI | Async-native, type-driven, gRPC-friendly |
| RPC | grpcio + protobuf | Industry standard for low-latency streaming |
| Ingestion | `websockets` + asyncio | Minimal, proven |
| Migrations | `alembic` | Standard for Postgres |
| Tests | `pytest`, `hypothesis` | Property tests for numerical correctness |
| Lint/Type | `ruff`, `mypy --strict` | Catch bugs before runtime |
| Containers | Docker Compose | Single-host deployment, zero orchestration tax |
| CI | GitHub Actions | Matches existing preference |
| Monitoring | Prometheus + Grafana | Open, industry standard |

## 9. Infrastructure & Deployment

**Local dev**: single `docker compose up` starts TimescaleDB, Redis, all services, Prometheus, Grafana, and a DB seed step.

**Production**: single VPS (Hetzner CX22, ~€5/mo, or Oracle free tier). Caddy as reverse proxy with auto-TLS. Docker Compose on the host. Backups: daily `pg_dump` to S3-compatible storage.

**CI/CD (GitHub Actions)**:
- On PR: lint, type check, unit tests, integration tests (against ephemeral TimescaleDB/Redis services).
- On merge to main: build and push images to GHCR, SSH to VPS, `docker compose pull && up -d`.

**Secrets**: `.env` on server only. Binance API keys are read-only (no trading scope). Rotated quarterly.

## 10. Milestones (6 weeks, part-time)

**Week 1 — Foundation**
- Repo skeleton, tooling (ruff, mypy, pre-commit), Docker Compose, DB schema + migrations.
- Ingestion for one symbol (BTCUSDT), trades only, writing to TimescaleDB.

**Week 2 — Ingestion complete**
- Order book L2 ingestion with sequence validation and snapshot resync.
- Five symbols. Redis hot cache. Stream publishing.
- First REST endpoint (`/snapshot`).

**Week 3 — Historical + feature engine**
- ETL backfill (6 months of 1m OHLCV).
- Feature engine library + property tests against `talib` oracle.
- `BatchDriver` computes and persists features for full history.

**Week 4 — Real-time features + signals**
- `StreamDriver` computes live features.
- Parity test harness (same input → same output across drivers) — gate for merge.
- Signal service with MA crossover and OB imbalance.
- WebSocket and gRPC signal streams.

**Week 5 — Backtester + observability**
- Backtester CLI producing HTML report.
- Prometheus metrics across all services.
- Grafana dashboard (committed as JSON).
- Structured logging everywhere.

**Week 6 — Polish + launch**
- Deploy to VPS, public Grafana read-only URL.
- README: architecture diagram, decision log, perf numbers (measured, not guessed), 60s demo video.
- Load test (e.g., `k6` against API, replay 24h of events in 10min through ingest pipeline).
- Write blog post / LinkedIn narrative.

## 11. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Scope creep | High | Strict v2 backlog. Every new idea goes there unless it's in milestones. |
| Binance WS edge cases (delisting, symbol rename) | Medium | Error telemetry + graceful degradation. Not fatal if one symbol fails. |
| TimescaleDB write bottleneck | Low | Batching already designed in. Measure, don't pre-optimize. |
| Drift between stream and batch features | Medium | Parity test enforced in CI. Fails the build if drift detected. |
| Reconnection storms (rate limiting by Binance) | Medium | Exponential backoff with jitter. Respect `429` responses. |

## 12. V2 Backlog (not in v1)

- Second exchange (Kraken) with cross-exchange spread features.
- Simple ML layer: XGBoost on features → signal, compared head-to-head vs. rule-based in backtester.
- Paper trading engine with simulated fills, realistic slippage model.
- Web UI for live signal monitoring (React + existing gRPC-Web).
- Feature registry with versioning.
- Multi-symbol portfolio-level backtest.

## 13. Portfolio Narrative

One-line pitch: *"Production-grade real-time market data infrastructure with integrated research pipeline, built to demonstrate backend engineering applied to quantitative trading systems."*

Interview talking points prepared in README:
1. Why one feature engine with two drivers (parity, research velocity).
2. How sequence-gap recovery works (the hard part of order book ingestion).
3. Backpressure strategy and what happens when the DB is slower than the stream.
4. Measured latency budget breakdown (WS → DB → stream → feature → signal → client).
5. Deployment tradeoffs: why single VPS over Kubernetes for this scale.

---

**Decision log** and **measured performance numbers** are the two README sections that differentiate this from 95% of portfolio projects. Keep them honest and specific.
