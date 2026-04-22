# MarketCore Milestone 1 Design

## Title

Capture and Replay Foundation

## Goal

Build a backend-only quant engine foundation that captures live market data for a small symbol set, stores canonical raw events durably, and replays captured windows exactly from storage.

This milestone is not about alpha research, strategy quality, or protocol breadth. It exists to prove deterministic event capture, replay correctness, and operational visibility.

## Project Positioning

MarketCore is a portfolio project for a backend engineer transitioning toward quant development. The strongest signal is not "I found a profitable strategy." The strongest signal is "I can build a reliable market-data system with deterministic semantics, replayability, and operational discipline."

## Scope

### In Scope

- Single-node deployment with Docker Compose
- Three symbols only
- Live ingestion of:
  - trades
  - fixed-interval top-of-book snapshots sampled every 250ms
- Canonical normalization of raw events
- Durable persistence to TimescaleDB
- Internal hot-path publication through Redis
- CLI-driven replay of captured windows
- Thin REST surface for health and basic query
- Prometheus metrics and Grafana dashboards

### Out of Scope

- Feature engine
- Signal generation
- Backtest analytics
- gRPC
- Full order book reconstruction
- Custom frontend
- Performance claims about strategy edge

## Architecture

### 1. Combined Ingest Service

One process owns exchange connectivity and symbol lifecycle for the three tracked symbols.

Internal responsibilities:
- exchange stream client
- top-of-book sampler
- canonical normalizer
- TimescaleDB writer
- Redis publisher
- health, lag, and reconnect tracking

This stays as one service in Milestone 1 to avoid architecture theater. Internal modular boundaries should still be clean.

### 2. Canonical Event Model

Milestone 1 supports exactly two raw event families:
- `trade`
- `top_of_book_snapshot`

Each canonical event must include:
- exchange
- normalized symbol
- event type
- event time
- ingest time
- exchange-native identifier where available
- fallback payload hash where native identifier is not available
- deterministic payload shape

Important rule:
- `event_time` and `ingest_time` serve different purposes and must never be mixed casually

### 3. Storage Model

Persist canonical raw events durably in TimescaleDB with indexes that support:
- symbol-scoped replay windows
- time-bounded scans
- event-type filtering

Redis is not the source of truth. It exists for hot-path publication and operational convenience. Replay correctness is anchored on TimescaleDB.

### 4. Replay Runner

A CLI tool selects a captured time window and re-emits the canonical event stream from storage.

Milestone 1 replay success means:
- exact reproduction of canonical raw events
- stable ordering rules
- deterministic serialization boundary

Milestone 1 does not yet claim downstream feature or signal parity.

### 5. Operability Surface

Thin REST endpoints should cover:
- `/health`
- dependency status
- last-message age
- current lag

Metrics should include at minimum:
- ingested trades total
- ingested top-of-book snapshots total
- reconnect count
- invalid event count
- dropped event count
- replay runs total
- replay failures total
- last successful write age

Grafana should make it obvious whether capture is healthy, delayed, or disconnected.

## Determinism Contract

The hero property for this milestone is:

`A captured live raw-event window can be replayed from storage with exact canonical event equality.`

This requires:
- deterministic canonicalization
- explicit ordering rules
- stable timestamp representation
- stable event identity logic

Event identity should prefer:
- exchange-native identifiers where available
- fallback hash only when the exchange does not provide a durable identity

## Failure Handling

Milestone 1 must not pretend happy-path behavior is enough.

Explicit design attention is required for:
- websocket disconnect and reconnect
- stale top-of-book state
- temporary TimescaleDB unavailability
- temporary Redis unavailability
- invalid or malformed exchange messages
- gaps in top-of-book sampling windows

The objective is not perfect fault tolerance. The objective is correct failure visibility and sane recovery behavior without silent corruption.

## Demo Artifact

The Milestone 1 deliverable should support a short recorded walkthrough that proves:
- live capture is running for three symbols
- trades and 250ms top-of-book snapshots are landing durably
- operational health and lag are visible
- a specific captured window can be replayed
- replay reproduces the canonical raw event stream exactly

The demo should show evidence, not just narration.

## Acceptance Criteria

- System runs locally through Docker Compose
- Live trades ingest works for three symbols
- 250ms top-of-book snapshots are produced for the same symbols
- Canonical raw events are persisted durably
- Replay CLI can replay a selected time window
- Replay output matches stored canonical raw events exactly
- Health and lag are exposed through thin REST and metrics
- Reconnects and write failures are observable

## Risks and Guardrails

### Risks

- Letting order-book concerns dominate the milestone
- Hiding weak determinism behind vague replay claims
- Overbuilding APIs before replay is trustworthy
- Mixing event-time and ingest-time semantics

### Guardrails

- Only two event families in Milestone 1
- No features or signals yet
- No gRPC
- No claim stronger than the system can actually prove
- Optimize for portfolio credibility over technology variety

## Why This Milestone Matters

If this milestone is weak, every later claim about parity, features, or signals becomes questionable. If this milestone is strong, later work sits on a defensible foundation.
