# Repository Guidelines

## Project Structure & Module Organization
`MarketCore-PRD.md` is the current source of truth for scope, architecture, and milestones. This repository is still PRD-first, so keep new code aligned with the module layout defined there: `ingest/`, `etl/`, `features/`, `signal/`, `api/`, `backtest/`, `ops/`, and `migrations/`. Put tests in `tests/`, with shared fixtures under `tests/fixtures/`. Commit operational assets such as Grafana JSON and Docker Compose files near `ops/` and the repo root.

## Build, Test, and Development Commands
The PRD standardizes on a Docker-first workflow. Prefer these commands once the scaffold exists:

- `docker compose up` - start TimescaleDB, Redis, services, Prometheus, and Grafana locally.
- `pytest -q` - run unit, property, and integration tests.
- `ruff check .` - lint Python code.
- `mypy --strict .` - run strict type checks.
- `pre-commit run --all-files` - enforce local quality gates before pushing.

If you add new scripts, keep command names simple and document them in `README.md`.

## Coding Style & Naming Conventions
Target Python 3.12. Use 4-space indentation, type hints on public functions, and small async-first service modules. Prefer `snake_case` for files, functions, and variables; `PascalCase` for classes; and clear service names such as `stream_driver.py` or `signal_service.py`. Keep the feature engine pure: no I/O inside `features/`. Use `ruff` for formatting/lint cleanup and keep `mypy --strict` passing.

## Testing Guidelines
Use `pytest` for all tests and `hypothesis` for numerical and parity checks. Name files `test_<module>.py`. Add parity coverage for shared stream/batch logic and oracle-based checks for indicators such as RSI or MACD. Treat integration tests against TimescaleDB and Redis as required for ingestion, API, and signal changes.

## Commit & Pull Request Guidelines
No Git history is present in this workspace, so no repo-specific commit convention can be inferred. Use short, imperative commit subjects, preferably Conventional Commit style such as `feat: add batch driver` or `fix: handle depth gap recovery`. PRs should include scope, risk, local verification steps, linked issues, and screenshots or sample payloads for API, dashboard, or report changes.

## Security & Configuration Tips
Do not commit `.env` files, API keys, or deployment secrets. Binance keys must remain read-only. Keep production-only credentials on the server, and document new environment variables in `README.md` with safe defaults or examples in `.env.example`.
