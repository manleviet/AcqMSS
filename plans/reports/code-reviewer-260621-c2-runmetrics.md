# Code Review — Stage C2: Generic metric reducer + RunMetrics alias + safety-net tests

Date: 2026-06-21 | Branch: feat/redesign-abc | Reviewer: code-reviewer
Scope: uncommitted working tree only — `conacq/eval/performance_metrics.py`, `conacq/eval/__init__.py`, new `tests/test_runmetrics_aggregation.py`. Prior committed stages out of scope.

## Verdict (headline)

**PASS — C2-as-delivered ships.** Reducer is provably behavior-preserving (programmatic 1:1 field-map proof + frozen-ref proven non-circular). Both decline/defer decisions justified. Only nits are non-blocking.

| Item | Verdict |
|------|---------|
| (1) Reducer behavior-preserving | **CONFIRMED — provably identical** |
| (3) EvaluationMetrics decline justified | **AGREE — justified (different inputs, not duplication)** |
| (4) Result-dataclass defer justified | **AGREE — legit balloon-split, not a skip** |
| (2) Frozen format intact | **CONFIRMED — to_dict unchanged, 19-file round-trip green** |
| (5) No weakened asserts / labels / scope / boundary | **CONFIRMED** |

Test state: full suite **552 passed, 0 warnings** (known-flaky parity test passed this run); new file **35 passed**; boundary guard **3 passed**; py_compile OK.

---

## VERIFY 1 — Reducer behavior-preserving (CRITICAL): CONFIRMED

Did not eyeball — proved it programmatically by parsing both implementations.

**1:1 field-map proof.** Parsed the OLD hand-unrolled `aggregate_metrics` (list-comp → `_stat4` unpack → ctor kwarg, with int-cast tracking) and the NEW `_METRIC_REGISTRY`, then diffed:
- OLD extended fields set: **96**. NEW extended fields set: **96**.
- `In OLD not NEW: []` and `In NEW not OLD: []` — exact set match.
- Per-field source attribute (`m.<attr>`) match: **0 mismatches**.
- Per-field int-cast match (min/max cast iff `cast_int`; mean/std never cast): **0 mismatches**.

**No field left at default (the key silent-regression risk).** `AggregatedPerformanceMetrics` has 98 fields-with-defaults; 2 are core (`n_mss_mean`, `n_kb_mean`, set in the ctor block), leaving **96 extended** — exactly the 96 the registry fills via `setattr`. Every extended field is written; none silently retains its `0.0`/`0` default. The new ctor constructs with the **byte-identical core block** as old (`n_runs`, `runtime_*`, `checks_*`, `memory_*`, `n_mss_mean`, `n_kb_mean`) then `setattr`s the rest. Dataclass is not frozen, so post-construction `setattr` is valid.

**Empty-list guard + core series extraction:** byte-identical to old (`if not metrics_list: raise ValueError`; same `runtimes/checks/memories/n_mss_list/n_kb_list` comprehensions).

**`to_dict()`:** untouched by the diff (grep-confirmed no `+` lines touch it). No external constructor sites of `AggregatedPerformanceMetrics` and no external `_stat4` users (grep across conacq/apps/tests) — the registry is the sole writer.

**Frozen-reference is REAL, not circular (CRITICAL sub-check).** Reconstructed the OLD committed `aggregate_metrics` from `git show HEAD:` into an isolated module, ran it on the test's two-run fixture, and compared `to_dict()` against the pinned `_FROZEN_REFERENCE` at rel_tol 1e-12: **exact match, key-for-key and value-for-value**. The pinned values are genuine pre-refactor outputs captured from the old implementation — the test is NOT trivially self-consistent with the new code.

→ **Verdict (1): behavior-preserving, proven.**

## VERIFY 2 — Frozen format intact: CONFIRMED

- `to_dict()` body unchanged → on-disk JSON keys/shape unchanged.
- No on-disk key renamed (96 extended field names identical; core block identical).
- 19-file `from_json`/`from_dict` round-trip over `data/results/congen/*.json` passes (parametrized, all green) — proves existing on-disk JSON still reads.
- `RunMetrics = PerformanceMetrics` is a pure alias (same class object; `test_runmetrics_is_performancemetrics` asserts identity) — no new fields, zero serialization impact.

## VERIFY 3 — EvaluationMetrics decline: AGREE (justified)

The three hand-built sites compute TP/TN/FP/FN over **fundamentally different input domains** than `compute_metrics`:

- `compute_metrics` (metrics.py:110): clause sets `Set[Tuple[int,...]]`; `TP = len(kb_set & oracle_set)` (set algebra on clauses).
- `kb_comparator.py:163`: **description strings** — `acquired_descriptions & fm_descriptions`.
- `kb_comparator.py:319`: **semantic entailment** — counts from `SemanticEquivalenceChecker` (entailed/unentailed CT/KB).
- `accuracy.py:117`: **example accept/reject classification** — iterates positive/negative examples through `_is_accepted`.

Routing these through `compute_metrics` would require synthesizing fake clause sets per domain purely so `kb_set & oracle_set` re-derives an already-computed TP — that adds contortion, not DRY. These are distinct evaluation strategies sharing only the 4-int output container `EvaluationMetrics`, which they correctly reuse. Independent verification matches the user's own. **Decline justified.**

## VERIFY 4 — Result-dataclass defer: AGREE (legit balloon-split, not a skip)

The three classes have genuinely divergent on-disk shapes, which the FROZEN-format constraint locks:
- `ConGenResult` (congen.py:37): in-memory, assumption-ID based (`kb_assumption_ids: List[int]`) — not serialized to the frozen format at all.
- `ConGenResultData` (result_loader.py:14): serializes counts under a **`statistics`** sub-key.
- `ConGenRunResult` (congen_runner.py:20): serializes runtime/call metrics under a **`performance`** sub-key, and inherits `BaseRunResult` (A4 metric-map dependency the plan's Red-team note says to KEEP).

Real on-disk folds carry BOTH `statistics` AND `performance` (plus `metrics`, `evaluation`) — the disk format is the union written by different stages. A single merged class keeping all serialization shapes byte-identical needs a divergent `to_dict()` dispatch = more complexity, not less. That is exactly the "balloon" the plan's Risk Assessment anticipated ("if it balloons → SPLIT … do NOT cut").

This was **split-and-landed, not skipped**: the c2 report documents it as a SPLIT with status DONE_WITH_CONCERNS, a concrete follow-up design (`UnifiedConGenResult` holding both algo- and runner-level fields, `from_json`/`from_dict` factory classmethods, `BaseRunResult` inheritance preserved, retirement path for `ConGenResult`), and next-step wiring. **Defer justified per the user's own "no deferral / split-and-land if it balloons" instruction — this is the split branch firing correctly.**

## VERIFY 5 — Asserts / labels / scope / boundary: CONFIRMED

- **No weakened assertions.** 35 tests assert real behavior: frozen-ref compared key-for-key against captured numbers (proven non-circular above); int-type assertions (`isinstance(agg.acqmss_calls_min, int)`) guard the cast; single-run std=0 branch; QuAcq-mixed-with-ConGen pinned values; reproducibility (double-run identity). `_values_equal` uses `math.isclose(rel_tol=1e-9)` for floats and exact `==` for ints — appropriate, not loosened.
- **No plan-stage labels in code** (grep for `C2|phase.?15|F\d+|redesign-abc|red.team|audit` in both changed files → none).
- **Scope clean:** only `conacq/eval/__init__.py`, `conacq/eval/performance_metrics.py`, + new `tests/`. No cross-package bleed.
- **Boundary guard green** (3 passed).

---

## Findings by severity

### Critical
None.

### High
None.

### Medium
None.

### Low (non-blocking nits — optional)

1. **Unused import** — `conacq/eval/performance_metrics.py:27`: `Dict` added to `from typing import Callable, Dict, List, Tuple, Optional` but `Dict` is never used in the file. `Callable`/`Tuple` are used (in `_ExtractorEntry`). Drop `Dict`.
   - Fix: `from typing import Callable, List, Tuple, Optional`

2. **Orphaned top-of-file comment** — `performance_metrics.py:29-30`: the comment block "RunMetrics is the canonical name…" sits right after imports, ~95 lines above the actual `RunMetrics = PerformanceMetrics` alias (which has its own adjacent comment at :129). The early block is redundant with the alias-site comment and floats with no nearby code. Remove the early one; keep the one at the alias.

3. **Registry `_stat4` re-walks `metrics_list` per metric (perf, not correctness)** — the loop does `values = [extractor(m) for m in metrics_list]` for each of 24 registry entries → 24 passes over the run list. Identical asymptotic behavior to the old version (which also built 24 separate comprehensions), so **no regression** — noting only that if `metrics_list` ever grows large this is O(metrics × runs); current run counts (CV folds, single digits) make this irrelevant. No action needed.

---

## Positive observations

- Frozen-reference test design is exemplary: values captured from the OLD implementation and pinned as literals, so the guard survives the API change by comparing CAPTURED numbers — independently verified non-circular. This is precisely what the plan's Red-team note demanded.
- Registry is self-documenting (header comment explains the 3-tuple contract; `cast_int` flag makes the int-cast explicit per metric rather than buried in 48 `int(...)` calls).
- `setattr` loop + per-metric `cast_int` collapses 159 lines to ~25 with zero behavioral drift — clean DRY win, KISS-compatible.
- Split decision was reported (DONE_WITH_CONCERNS) with a concrete follow-up design rather than silently dropped — correct orchestration hygiene.

---

## Recommended actions

1. (Optional, Low) Remove unused `Dict` import (perf_metrics.py:27).
2. (Optional, Low) Delete the redundant early RunMetrics comment (perf_metrics.py:29-30).
3. Land C2 as-is — gates are green. Track the `UnifiedConGenResult` follow-up as a separate stage (already sketched in the c2 fullstack report).

## Metrics
- Behavior-preservation: proven (96/96 fields exact; frozen-ref == old output at 1e-12).
- Tests: 552 passed / 0 warnings (full); 35 passed (new file); 3 passed (boundary).
- Lint: 1 unused import (Low).
- Type/compile: py_compile OK.

## Unresolved questions
None. All five VERIFY items resolved with grep/exec-level evidence; confidence ≥95% on each verdict.
