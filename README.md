# MarketCore

Backend quant engine focused on deterministic replay, canonical market data capture, and operationally reliable signal infrastructure.

MarketCore is a market-data and replay foundation for quant workflows where event semantics matter. The project captures live market data, normalizes it into canonical raw events, stores those events durably, and builds deterministic replay primitives on top of that storage layer. The goal is not to make early alpha claims. The goal is to make later claims about parity, features, signals, and backtests defensible.

## Why This Matters

Many trading projects can calculate indicators. Far fewer make replay correctness, canonical event identity, and ordering semantics explicit. Without that foundation, later claims about live-vs-backtest parity are weak.

MarketCore is built to make those guarantees concrete:
- canonical raw events preserve source identity and payload hash
- replay ordering preserves source, timestamp, and ingest-order semantics
- top-of-book sampling is deterministic at `250ms`
- replay equality checks reject ambiguous or non-canonical payload forms
- local verification runs with tests, linting, and strict typing

## Current Milestone

This repository is currently in `Milestone 1: Capture and Replay Foundation`.

Current scope:
- live `trade` capture foundation
- `250ms` fixed-interval top-of-book snapshot foundation
- canonical raw-event normalization
- raw-event schema and storage foundation in TimescaleDB
- deterministic replay helpers and equality checks
- minimal health, metrics, and operator stack scaffold

## Architecture

Current system shape:

`Binance stream -> ingest normalization -> canonical raw events -> TimescaleDB -> replay path -> future feature/signal parity`

Repository modules:
- `ingest/`
  normalization, deterministic top-of-book sampling, storage and publication foundations
- `backtest/`
  replay equality checks and replay-path primitives
- `api/`
  minimal health and metrics-facing surface
- `ops/`
  local Docker Compose, Prometheus, and Grafana scaffold
- `migrations/`
  raw-event schema foundation
- `tests/`
  deterministic behavior, normalization, replay, storage, and operator-stack coverage

## Local Setup

Create and use a local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi pydantic pydantic-settings pytest prometheus-client alembic sqlalchemy asyncpg redis websockets structlog hypothesis mypy ruff uvicorn httpx
```

If `.venv` does not exist yet, create one first with a local Python interpreter, then install the baseline dependencies used by the repo.

The operator stack scaffold lives under `ops/`, but it should be treated as Milestone 1 infrastructure scaffolding rather than a complete live deployment path.

## Verification

Run the current verification suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy --strict .
```

These checks currently pass on the repository snapshot in this branch.

## Roadmap

- `Milestone 1`
  capture and replay foundation
- `Milestone 2`
  derived bars and shared feature engine
- `Milestone 3`
  live features and simple signal emission
- `Milestone 4`
  parity validation over replayed live windows
- `Milestone 5`
  backtesting and research workflow

## Current Limitations

- the full live ingest loop is not implemented yet
- feature and signal pipelines are not implemented yet
- historical backtesting reports and research workflow are not implemented yet
- the operator stack is scaffold-level, not a final deployment setup
- the local environment is currently bootstrapped through a repo-local `.venv`
