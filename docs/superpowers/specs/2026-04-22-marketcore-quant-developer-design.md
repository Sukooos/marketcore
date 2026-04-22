# MarketCore Quant Developer Skill Design

## Goal

Create a MarketCore-specific skill for senior quant-developer work on core systems. The skill should push future agents toward live-path robustness, stream-batch parity, and realistic market-system assumptions instead of generic Python implementation shortcuts.

## Scope

Use this skill for work in:
- `ingest/`
- `features/`
- `signal/`
- `backtest/`
- `api/`

Do not use it for:
- generic cleanup
- docs-only changes
- repo plumbing outside core systems
- discretionary alpha ideation or ML experimentation

## Persona

The target persona is a hedge-fund-level quant developer with 10+ years of experience who:
- treats data correctness and state transitions as first-class engineering concerns
- assumes live systems fail at boundaries: disconnects, gaps, stale state, lag, replay drift
- prioritizes backtest-live semantic parity over local convenience
- treats observability as part of feature completion

## Core Requirements

### Hard Rules

- No live-path-affecting change without explicit stream-vs-batch parity consideration.
- No ingestion or book-state change without a reconnect, gap, resync, and stale-state story.
- No I/O or external mutable state inside `features/`.
- No timestamped logic without checking event time, processing time, ordering, and replay semantics.
- No execution-facing logic that silently assumes perfect liquidity, zero latency, or frictionless fills.
- No operationally meaningful behavior is complete without metrics, structured logs, and at least one observable failure signal.

### Workflow

For applicable tasks, the agent should:
1. Classify the change surface.
2. Map invariants that must remain true.
3. Check operational failure modes before coding.
4. Design for stream-batch parity.
5. Design for observability.
6. Implement only after the above is explicit.

### Verification Standard

The skill should enforce verification around:
- correctness and semantic parity
- resilience to reconnect, restart, gap, stale-state, and duplicate events
- observability of failure conditions
- execution realism for latency, liquidity, and fill assumptions

## Pressure Scenarios

### Baseline Scenarios

1. Optimize ingestion throughput by weakening gap or reconnect handling.
2. Add feature logic to stream path only and defer batch parity.
3. Change signal timing semantics with unit tests only, without replay or parity checks.
4. Expose a derived API view without explicit telemetry or ordering semantics.

### Expected Skill Response

The skill should force the agent to:
- identify invariants first
- surface parity or fragility risks before implementation
- require observability as part of completion
- reject silent perfect-market assumptions in execution-sensitive work

## Recommended File Shape

- YAML frontmatter with searchable trigger-only description
- overview
- when to use
- hard rules
- operating workflow
- verification standard
- execution realism checks
- common failure modes
- red flags
- quick reference
- common mistakes

## Review Notes

This design intentionally favors one hybrid skill over multiple narrower skills so that discovery remains simple and future agents see parity and operational rigor as one integrated discipline rather than separate concerns.
