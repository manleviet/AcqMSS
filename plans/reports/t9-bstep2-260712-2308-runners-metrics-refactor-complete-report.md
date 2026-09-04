# T9 — BƯỚC 2 refactor complete (green, no commit)

**Date:** 2026-07-12 · **Branch:** feat/redesign-abc-v2 · **Spec:** `Cowork/explanation/t9-design.md` (P2 disjoint, confirmed)
**Suite: 407 passed** · net 7 tests · guard 6 rules · **no commit**.

## (a) Delta-check (impl-plan §T9 updated in place)
D1 +`metrics.py`. D2 disjoint tables module-level. D3 +guard rule 6. D4 +config move. D5 5-test net.
D6 **dropped [A4] runner-boilerplate dedup → T17 debt** (out of design scope). D7 core subpackages =
algorithms/bias/example_generators/examples/oracle/runners (design's 'models' isn't a conacq dir); 5 apps import config, not 6.

## (b) Net-first: tests 1–3 GREEN on OLD code BEFORE refactor
`tests/test_t9_metrics_safety_net.py` ran `4 passed` at **22:43:48→49**, before a single refactor line
existed (prior turn / net-gate report). Post-refactor the net is **7 passed** (tests 1–6 + the ConGen/QuAcq
schema split). Test 2 re-expressed per-algorithm against the SAME real-data literal (slices), not the reducer.

## (c) Extraction byte-diff EMPTY
`extract_results` (NEW code) over `data/results/congen` vs the OLD-code golden → **md + tex byte-identical**.
Test 1 pins this permanently against a committed golden fixture.

## (d) Changeset (21 files, tracked; excl. paper/ plans/)
NEW: `conacq/runners/metrics.py` (217 LOC), `tests/test_t9_metrics_safety_net.py`, `tests/resources/t9_extraction_golden/{md,tex}`.
MOVED: `conacq/eval/config.py → conacq/config.py`. DELETED: `conacq/eval/performance_metrics.py` (652 LOC).
MODIFIED: base_runner, congen_runner, quacq_runner, cross_validation, eval/__init__, test_boundary_guard,
test_evaluation, 5 apps, 3 docs, impl-plan.

## What landed (ADR-0006 decision, complete + green)
- **metrics.py**: `Kind`/`MetricSpec` + disjoint `CONGEN_METRICS`/`QUACQ_METRICS` (abbreviations declared in `group`)
  + `RunMetrics` (dict-backed, `to_dict` derived from spec) + `collect(profiler, spec, extra)` (replaces ① hand-extract ×2)
  + generic `aggregate(runs)` ~40 LOC (replaces ③④ ~365 lines) applying the §3.2 naming rule.
- **Cycle killed structurally**: runners no longer import eval (all 3 styles gone: deferred, absolute, relative);
  cross_validation imports `aggregate` from `conacq.runners.metrics` (eval→runners, the allowed direction).
- **Guard rule 6** (conacq core ⊥ conacq.eval), catches absolute + relative imports.
- **config → conacq/config.py**, 5 apps + eval facade repointed.
- Naming-rule claim (§3.2) verified 100% against real data (only `kb_size` is a >1-metric group).

## (e) Deviations / flags
1. **Test-2 P2 (disjoint)** — confirmed by Cowork; new ConGen block = 13 groups; legacy 29-group files untouched.
   Test 6 pins mixed old/new directories extract correctly.
2. **[A4] runner-lifecycle dedup → T17** (Cowork-approved defer).
3. **D7 mechanical** — 5 apps (not 6); 'models' not a conacq subpackage.
4. **⚠️ UnifiedConGenResult (impl-plan item 7 / `[71c1511]`) NOT done** — deferred. Reason: it is a *result-type
   merge* (`ConGenRunResult` + `ConGenResultData`), NOT part of the ADR-0006 decision, invasive (6+ touchpoints:
   congen_runner, result_loader, kb_comparator, cross_validation, runners/__init__, tests), and separable. Deferred
   to avoid a half-merge at context depth. `ConGenResultData` / `ConGenRunResult` remain as-is and green. Needs a
   fresh turn or Cowork's word to finish.

## Unresolved questions
1. Finish UnifiedConGenResult now (next turn) or accept the deferral within T9?
