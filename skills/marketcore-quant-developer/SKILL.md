---
name: marketcore-quant-developer
description: Use when working on MarketCore core systems in ingest, features, signal, backtest, or api where live-path robustness, stream-batch parity, timestamp semantics, or market microstructure assumptions could be degraded
---

# MarketCore Quant Developer

## Overview

Work like a senior quant developer responsible for keeping MarketCore correct under live market conditions, not just locally passing tests.

**Core principle:** preserve operational robustness and stream-batch parity before optimizing convenience, speed, or local elegance.

## When to Use

Use for changes in:
- `ingest/`
- `features/`
- `signal/`
- `backtest/`
- `api/`

Use this especially when the task can affect:
- reconnect, resync, or stale-state behavior
- stream vs. batch feature or signal semantics
- event ordering, timestamps, or replay behavior
- order book state, imbalance, latency, or fill assumptions
- live observability or production diagnosis

Do not use for:
- generic cleanup outside core systems
- docs-only changes
- repo plumbing without behavioral impact
- discretionary alpha ideation unrelated to MarketCore system behavior

## Hard Rules

- No live-path-affecting change without explicit stream-vs-batch parity consideration.
- No ingestion or order book change without a reconnect, gap, resync, and stale-state story.
- No I/O, network access, database access, or external mutable state inside `features/`.
- No timestamped logic without checking event time, processing time, ordering, and replay semantics.
- No execution-facing logic with silent perfect-market assumptions such as zero latency, full liquidity, or guaranteed fills.
- No operationally meaningful behavior is complete without metrics, structured logs, and at least one observable failure signal.

## Operating Workflow

1. Classify the surface.
   Determine whether the change touches ingestion, feature computation, signal generation, replay/backtest, API projection, or cross-cutting state and observability.
2. Map the invariants.
   Write down what must stay true before changing code.
3. Check failure modes first.
   Consider disconnects, sequence gaps, snapshot recovery, Redis or DB restart, stale cache, lag bursts, duplicates, and out-of-order events.
4. Design for parity.
   If live and replay or batch paths should agree, share the logic directly or define how parity will be proven.
5. Design for observability.
   Define the metric, structured log fields, health signal, or parity hook that would reveal the failure in production.
6. Only then implement.
   Implementation is not complete until it preserves invariants and verification covers the relevant failure surface.

## Verification Standard

- Prefer invariant-driven tests over coverage-driven tests.
- For shared live and backtest behavior, require parity-oriented verification.
- For ingestion changes, verify recovery behavior, not only happy-path parsing.
- For feature changes, prefer oracle or property-based checks when numerical references exist.
- For signal changes, verify timestamp alignment, state transitions, and replay consistency.
- For API changes, verify the API does not silently change semantics from the underlying feature or signal store.

## Execution Realism Checks

- Check whether latency changes the meaning of the signal or snapshot.
- Check whether the book view can be stale by the time a decision is consumed.
- Check whether imbalance or microstructure features rely on unstable top-of-book state.
- Check whether replay order matches live causal order closely enough to justify comparison.
- Check whether any evaluation assumes fills at observed prices without queue position, spread, impact, or delay.

## Common Failure Modes

| Failure mode | What usually went wrong | Required response |
|---|---|---|
| `ops-fragility` | Happy-path logic ignored disconnect, restart, lag, or resync behavior | Add recovery handling and make failure observable |
| `parity-break` | Stream and batch paths diverged in logic, timing, or data preparation | Share logic or add explicit parity proof |
| `hidden-state-drift` | External mutable state leaked into supposedly pure logic | Push state to drivers or services, keep `features/` pure |
| `timestamp-misuse` | Event time and processing time were mixed or ordering assumptions were implicit | Make timestamps explicit and test replay semantics |
| `replay-mismatch` | Historical replay used cleaner or differently ordered inputs than live | Align input semantics and prove comparison is valid |

## Red Flags

If you catch yourself thinking any of these, stop and re-check the design:

- "It works in backtest, so live should be fine."
- "Reconnect logic is edge-case polish."
- "We can add metrics later."
- "This path only affects one service."
- "The batch driver is close enough."
- "We can backfill parity later."
- "Unit tests are enough for timing changes."

## Quick Reference

| Change type | Minimum checks |
|---|---|
| Ingestion | gap handling, reconnect, resync, stale-state, duplicate and ordering behavior, telemetry |
| Features | purity, timestamp semantics, oracle or property checks, stream-batch parity |
| Signals | state transitions, replay consistency, timing alignment, latency sensitivity |
| Backtest | input equivalence, replay ordering, execution realism, parity with live semantics |
| API | semantic fidelity to source data, ordering clarity, telemetry for failure or lag |

## Common Mistakes

- Treating replay as equivalent to live without proving ordering and timestamp assumptions.
- Shipping a feature that passes unit tests but has no parity check across live and batch paths.
- Using cleaner historical data than the live path consumes.
- Hiding mutable state inside feature calculations because it feels convenient.
- Exposing derived outputs without the logs or metrics needed to diagnose divergence.

## Bottom Line

In MarketCore core systems, "mostly correct" is failure. Preserve parity, surface operational failure early, and make market-system assumptions explicit.
