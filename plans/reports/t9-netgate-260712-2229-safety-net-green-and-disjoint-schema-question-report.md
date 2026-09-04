# T9 — net gate reached (tests 1–3 green on OLD code) + one design question

**Date:** 2026-07-12 · **Branch:** feat/redesign-abc-v2 · **Spec:** `Cowork/explanation/t9-design.md`
**Status:** BƯỚC 1 done (net-first). STOPPED at design's mandated hard gate, before BƯỚC 2 refactor.
**No commit. No refactor line written yet.**

## (a) Delta-check — impl-plan §T9 vs t9-design.md (design wins; impl-plan updated in place)

| # | Delta | Resolution |
|---|---|---|
| D1 | impl-plan named only `unified_result.py`; design §3.4 needs a separate `conacq/runners/metrics.py` (Kind/MetricSpec/CONGEN_METRICS/QUACQ_METRICS/RunMetrics/collect/aggregate) | added as core |
| D2 | impl-plan [A4] "BaseRunner owns metric map"; design = two disjoint module-level tables | tables module-level |
| D3 | impl-plan silent on guard rule 6 (conacq core ⊥ conacq.eval) | added (abs + relative) |
| D4 | impl-plan silent on `eval/config.py → conacq/config.py` move | added (+5 apps + eval facade) |
| D5 | impl-plan test = "aggregation pin" only; design = 5 tests, extraction-diff = real acceptance | adopted all 5 |
| **D6** | impl-plan [A4] "2 runners drop shuffle+profiling dup" = runner-lifecycle dedup, NOT in design (§3 is metrics-only) | **DROPPED from T9 (scope creep) → defer** |
| D7 | design §3.4 says "six apps" import config; actual = 5 (`run_evaluation/run_cv/run_congen/run_compare/run_quacq`) | mechanical delta → Cowork sync brief |

## (b) Net-first evidence — tests 1–3 GREEN on OLD code, before refactor

`tests/test_t9_metrics_safety_net.py` (4 tests) + golden fixtures `tests/resources/t9_extraction_golden/{md,tex}`:
- **T1** extraction-diff (real acceptance): re-run `apps.extract_results` over `data/results/congen` → byte-identical to frozen golden.
- **T2** schema-pin LITERAL: 29-group aggregated schema copied verbatim from a real congen file (not code-derived).
- **T3** from_json sweep: every recorded CV JSON parses.

```
22:43:48 net-run-start
tests/test_t9_metrics_safety_net.py ....  4 passed in 0.08s
22:43:49 net-run-end
```
Timestamp precedes any refactor code — the net was woven before the fall.

## Load-bearing claim (§3.2 naming rule) — VERIFIED against real data
Dumped every group's stat-keys from a real congen file. Only `kb_size` is a >1-metric group
(`n_mss_mean`/`n_kb_mean` → `{key}_{stat}`); all 27 others are single-metric (`{stat}{unit}`).
The rule reproduces the entire frozen schema. Claim holds — no DỪNG on that axis.

## Read-path proof (why disjoint is byte-safe)
- `extract_results.load_cv_result` reads only 4 aggregated groups: `runtime`/`consistency_checks`/`memory`/`kb_size` (all ConGen-owned).
- `result_loader.from_json` reads no `performance` block at all (only kb/statistics/metadata).
- We do not regenerate `data/results/`.
⇒ Dropping QuAcq groups from the ConGen table cannot move a table cell or break a loader.

## ⚠️ Design question (surfaced, NOT silently resolved) — one point, changes container shape

The real recorded ConGen JSON contains **all 29 aggregated groups**, incl. 16 zeroed QuAcq groups
(union-container pollution). Two design statements pull opposite ways:

- **§3.1 / §5 / §6 / ADR-0006 #2** → **disjoint**: "QuAcq no longer pollutes ConGen's container",
  "+0 for everyone". New ConGen block = 13 groups.
- **§4-test2 wording** → "pin a real congen block ... assert aggregate() emits **exactly that**"
  reads as if new ConGen aggregate reproduces all 29 groups.

**My read (confidence ~90%): P2 = disjoint** (4 explicit statements vs 1 loose test-wording).
**It does not affect the hard acceptance** (read-path proof above). Test 2 stays literal: the 29-group
literal is the anchor; post-refactor the disjoint ConGen reducer is pinned against its **prefix** (13
groups), QuAcq against the **suffix** (16 groups) — sliced from the same literal, never code-derived.
Being wrong is a cheap declarative fix (add QuAcq specs to the ConGen table).

**Ask:** confirm P2 (disjoint; new ConGen JSON drops zeroed QuAcq groups) so I execute BƯỚC 2, OR
choose P1 (ConGen keeps zeroed QuAcq groups for on-disk schema continuity).

## BƯỚC 2 (on confirmation) — refactor
metrics.py (spec tables + RunMetrics + collect + aggregate) → delete performance_metrics.py →
runners use collect() (kill 3 eval-import styles + deferred import) → cross_validation imports aggregate
from runners → guard rule 6 → config move → UnifiedConGenResult → tests 4–5 + rewrite
test_evaluation::TestPerformanceMetrics to new API. Then (c) diff empty, (d) changeset, (e) deviations.

## Unresolved questions
1. P1 vs P2 (above) — the only blocker for BƯỚC 2.
