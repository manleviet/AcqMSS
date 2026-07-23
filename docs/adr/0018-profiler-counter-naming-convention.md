# ADR-0018: Profiler counter naming convention (conmin_ / congen_ / shared_)

- Status: Accepted
- Date: 2026-07-23
- Deciders: Viet-Man (Cowork), CC

## Context

ConMin (AAAI paper) and ConGen (SoSyM paper) are separate papers sharing one repo and
one profiler. The §9c consistency-check taxonomy adds several new per-call-site counters
(gate, AcqMinCover rejection/QuickXplain, AcqMSS Stage-1). Some call-sites live in code
that ONLY ConMin runs (`conmin/`), others in code BOTH algorithms run (`acqmss/`). Without
a naming rule it is unclear, at a counter's site, whether touching it can perturb ConGen's
frozen numbers — and the metrics safety net (`test_t9_metrics_safety_net`) treats any
emitted-but-undeclared key as a failure.

## Decision

Prefix every **new** profiler counter by the code that owns its call-site:

- `conmin_` — emitted only by ConMin-only code (`conmin/`). Zero risk to ConGen.
- `congen_` — emitted only by ConGen-only code (already the de-facto convention).
- `shared_` — emitted by code both algorithms call (e.g. `acqmss/`). Adding one is
  additive: it must NOT change any existing counter, so ConGen's declared metrics stay
  byte-identical. `shared_*` keys are **always-allowed** in every algorithm's
  metric-map completeness check (they are never an "undeclared" metric for one algo).

**New-only; do NOT retrofit** the existing unprefixed counters (`paper_consistency_checks`,
`is_consistent_calls`, `acqmss_runtime`, …). Retrofitting would churn the frozen on-disk
schema + the recorded ConGen results for no AAAI benefit. Revisit the rename of legacy
counters **post-AAAI** (a SoSyM-revision cleanup, not a blocker).

## Applied in this change (§9c taxonomy, P4d)

- Renamed (ConMin-only): `cover_rejection_checks → conmin_cover_rejection_checks`,
  `cover_quickxplain_checks → conmin_cover_quickxplain_checks`, `acqmincover_runtime →
  conmin_acqmincover_runtime`.
- New (ConMin-only): `conmin_admpool_gate_checks` (Stage-0 gate, per-e⁺).
- New (shared): `shared_admpool_checks` (AcqMSS Stage-1 CONSISTENT test, per-e⁺; ConGen
  emits it too, additively).
- The reported paper total (SoSyM R1-Q4) is the SUM of the classified counters
  (gate + admpool + cover rejection + cover QuickXplain + redundancy), computed on the
  ConMin side — NOT the auto-counted `is_consistent*` primitives (avoids double-count).

## Consequences

- A counter's prefix states its blast radius at the call-site; a `shared_` touch signals
  "prove ConGen byte-identical" (done: ConGen tripwires + `test_congen_metric_map_is_complete`
  with the `shared_*` always-allowed rule stay green).
- Legacy unprefixed counters remain until a post-AAAI cleanup; the convention binds only
  new counters, so mixed prefixes coexist by design.
