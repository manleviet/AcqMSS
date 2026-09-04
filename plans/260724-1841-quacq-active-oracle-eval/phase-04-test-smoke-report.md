---
phase: 4
title: Test Smoke & Report
status: completed
effort: M
priority: P1
dependencies:
  - 3
---

# Phase 4: Test Smoke & Report

## Overview

**This phase is a GO/NO-GO GATE, not just a smoke test (red-team C-1/H-2).** Prove suite green
and existing conditions value-unchanged, then decide — on evidence — whether oracle-mode QuAcq
actually beats the strawman before Viet-Man spends a timed 5-KB sweep. The plan's premise is
contested by the paper's own example-first (SAT-generating) results (sem-F1 ≤ 0.105, structural
cause; `paper/evaluation.tex:318,374-378,387`), so the gate must clear that band, not merely beat
the crippled example-only rows. **CC runs only untimed smokes** (through `/tmp`); Viet-Man runs
the timed sweep on the quiet Apple M1 Pro after busybox — only if the gate passes.

## Requirements

- Green: `PYTHONPATH=. pytest tests/ -q` (incl. `test_quacq.py`, `test_conmin.py`, boundary/metrics).
- Value-identical: ConGen/ConMin acquisition outputs byte-identical; A/C/C∪S/QuAcq eval **values**
  identical (ignoring the additive `convergence_reason`/provenance columns).
- Gate evidence: on REAL-FM-7 **and one mid-size KB (fqa or arcade-game)**, oracle-mode sem-F1 vs
  example-only vs the paper's example-first band, `oracle_queries`, `convergence_reason`; proof
  `QueryProvider` + `DiscriminatingGenerator` + FM oracle are exercised; worst-case single-iteration
  wall-clock (M-1); per-KB feasibility.

## Pre-registered gate threshold (set BEFORE running — no cherry-picking, H-2)

- **PASS** iff on **both** REAL-FM-7 and the mid-size KB: oracle-mode `sem_f1` ≥ **0.15**
  (materially above the paper's ≤0.105 example-first band) **and** ≥ 2× the example-only `sem_f1`,
  with `convergence_reason ∈ {empty_bias, no_query}` (converged, not budget-capped).
- **NO-GO** otherwise → QuAcq-active is reported as an *informational* row with a threats-to-validity
  note (C-1/C-2/C-3), not as a "fixed active baseline." Either outcome goes to CW Main.
  (Threshold is a starting proposal; CW Main may adjust — record whatever is used.)

## Tests to add / run

- Phase-1 unit tests (`tests/test_quacq.py`): tiny-`timeout_s` → `convergence_reason='timeout'`
  + partial KB; `timeout_s=None` no-op; generous timeout + small `max_queries` → `max_queries`.
- Evaluator test (`tests/test_conmin.py`): REAL-FM-7 `evaluate_kb_example(..., active_res=<learned>,
  qa_max_queries=small, qa_timeout_s=large)` returns `condition='QuAcq-active'` rows with populated
  `oracle_queries`/`convergence_reason`/provenance, keys equal to the other scored rows
  (`set(active_row) == set(quacq_row)`).
- H-3 test: a `convergence_reason='max_queries'` QuAcq-active fold is counted (`n_maxq`) and
  **excluded** from the metric mean in `aggregate_cv` (assert it doesn't move `sem_f1_mean`).
- H-5 test: `_merge_per_kb` over a dir mixing a with-column JSON and a without-column JSON emits
  **no** schema warning and produces a union-column CSV with blanks.
- Regression guard: A/C/C∪S/QuAcq rows from `run_quacq_active=False` equal pre-change values.

## Smoke recipe (untimed; ALL output to /tmp — never the committed dir, M-4)

```bash
cd /Users/manleviet/Development/GitHub/AcqMSS
PYTHONPATH=. pytest tests/ -q                                  # suite green
CFG=apps/conf_conmin/run_conmin_eval_config.toml
OUT=/tmp/qa_smoke   # NON-destructive: committed data/results_conmin/ stays git-clean

# gate KBs — REAL-FM-7 (tiny) + one mid-size; both untimed, both to /tmp
python -m apps.run_conmin_eval $CFG --kb REAL-FM-7 -o $OUT -v          # 14 feat, |B|=295
python -m apps.run_conmin_eval $CFG --kb fqa       -o $OUT -v          # 179 feat, |B|=459 (mid)

# inspect example-only vs oracle-mode:
python3 - <<'PY'
import csv, glob
for f in sorted(glob.glob('/tmp/qa_smoke/*_long.csv')):
    rows=list(csv.DictReader(open(f)))
    for c in ('QuAcq','QuAcq-active'):
        r=[x for x in rows if x['condition']==c and x['example_set']=='ff']
        if r:
            x=r[0]; print(f.split('/')[-1], c, 'n_kb=',x['n_kb'],'sem_f1=',x.get('sem_f1'),
                           'oq=',x.get('oracle_queries'),'conv=',x.get('convergence_reason'))
PY
```

Expected if the premise holds: QuAcq-active `oracle_queries` in the active-budget range, `n_kb`
materially > example-only, `sem_f1` ≥ gate threshold on **both** KBs, `convergence_reason`
converged. If fqa lands ≈ 0.05 (the example-first band) → **NO-GO**, premise refuted, escalate.

## Value-identical / unchanged-conditions check (also to /tmp)

```bash
python -m apps.run_conmin_eval $CFG --kb REAL-FM-7 --no-quacq-active -o /tmp/qa_noactive -v
# diff A/C/C∪S/QuAcq VALUES vs the committed baseline data/results_conmin/REAL-FM-7_long.csv,
# dropping the additive convergence_reason/qa_* columns first (value-identical, not byte).
```

## Worst-case iteration + feasibility (for the report — not a timed run)

- **[M-1]** During the fqa smoke, log the slowest single outer-iteration wall-clock (FindScope+FindC)
  so the timeout-overrun bound is measured, not guessed. State it: the 400 s wall-clock is a floor
  that one iteration can exceed by that amount.
- Feasibility = 1 learn/KB (H-6) × per-learn wall-clock (deterministic if `max_queries` fires
  first). Fill from the two smokes + |B|/feat scaling:

| KB | #feat | \|B\| | est. per-learn | learns/KB | convergence expected |
|---|---|---|---|---|---|
| REAL-FM-7 | 14 | 295 | (measure) | 1 | empty_bias/no_query |
| fqa | 179 | 459 | (measure) | 1 | ? |
| arcade-game | 65 | 1,755 | ? | 1 | ? |
| REAL-FM-4 | 291 | 2,079 | ? | 1 | ? |
| busybox-1.18.0 | 854 | 6,635 | ? | 1 | `max_queries` unless budget≫|B| (H-4) |

## Report to CW Impl (`plans/reports/from-cc-to-cw-impl-260724-quacq-active-oracle-smoke-report.md`)

1. Exact oracle-mode invocation + where it plugs in (apps-layer per-KB learn, H-6).
2. **Gate table**: example-only vs oracle-mode vs paper example-first band (sem-F1, `oracle_queries`,
   `convergence_reason`, `n_kb`) on REAL-FM-7 **and** fqa; PASS/NO-GO verdict vs the threshold.
3. Confirmation: QueryProvider + DiscriminatingGenerator + FM oracle exercised; suite green (count);
   A/C/C∪S/QuAcq value-identical; `--merge` tolerance verified.
4. Worst-case single-iteration wall-clock (M-1) + per-KB feasibility.
5. **Threats to validity → CW Main** (C-1 premise, C-2 budget asymmetry, C-3 oracle=grader,
   C-2↔C-4 tension) + the two prompt decisions (which becomes paper's "QuAcq (active)" column;
   confirm machine = Apple M1 Pro 8-core 16 GB).
6. Unresolved questions.

## Success Criteria

- [ ] `PYTHONPATH=. pytest tests/ -q` green (incl. new timeout/H-3/H-5 tests).
- [ ] Gate run on REAL-FM-7 **and** fqa; PASS/NO-GO recorded vs the pre-registered threshold.
- [ ] All smoke output under `/tmp`; committed `data/results_conmin/` untouched (git-clean).
- [ ] A/C/C∪S/QuAcq **values** identical to baseline (additive columns dropped for the diff).
- [ ] Worst-case iteration wall-clock measured; feasibility table filled.
- [ ] Report (with threats-to-validity) written; CW Impl notified.

## Risk Assessment

- **[M-4] Baseline destruction**: never run a QuAcq-active-ON smoke into the committed dir — every
  command here uses `-o /tmp/...`, keeping `data/results_conmin/` git-clean and the baseline intact.
- **[C-1/H-2] Cherry-picked acceptance**: REAL-FM-7 (|B|=295, 3-example test folds) proves nothing
  about busybox — the gate REQUIRES a mid-size KB (fqa) too, with a pre-registered threshold.
- **Don't perturb the live sweep**: untimed smokes only; no timed multi-KB run while busybox runs.
- **REAL-FM-7 too small to stress the timeout**: exercise the `'timeout'` path via the tiny-`timeout_s`
  unit test, not the smoke KB.
- **[NO-GO is a valid outcome]**: if the gate fails, that is the deliverable (premise refuted) — do
  NOT tune thresholds to force a pass; report it straight to CW Main.
