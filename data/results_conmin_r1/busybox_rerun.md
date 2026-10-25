# Busybox (KB5) — exact re-run for the revision (deferred)

Not run (CPU reserved). The current figures for busybox are analytic bounds from the committed
rows (`semantic_root_bounds_from_committed.py` → `semantic_bounds_busybox-1.18.0.csv`). No
busybox learned KB is stored anywhere, so every cell needs a re-learn. Table-5 cells only:
samplings `ff`, `rs_1n` (busybox has no rs_2n/rs_3n/rs_m; 2cov is excluded from Table 5). Add a
`--es 2cov` pass as well: the consistency check (correction 3) covers 2-COV, and SoSyM's busybox
2-COV ConGen folds are all UNSAT with the root axiom.

## 1. Re-learn and persist — one command

```bash
PYTHONPATH=. nohup nice -n 10 uv run --no-sync python -m apps.conmin_r1.relearn_kbs_with_persistence \
  --kbs busybox-1.18.0 --es ff rs_1n --learn-quacq-active --workers 6 \
  > data/results_conmin_r1/logs/relearn_busybox.log 2>&1 &
```

- **QuAcq-active** is learned first (sequential, ≥ 10 h). The committed run stopped on the WALL
  CLOCK (36,000 s) at 1,901 queries, size 11 — why busybox is `NON_ANCHORABLE_QUACQ_ACTIVE`.
  `QA_BUDGET` sets `max_queries=1901`, timeout 72,000 s, so the deterministic rail fires at the
  committed stopping point. **Acceptance:** log line
  `busybox-1.18.0 QuAcq-active: size=11 queries=1901 reason=max_queries`. If size ≠ 11, the
  clock cut mid-FindScope/FindC and the committed theory is not reproducible — keep the bounds.
- Then 6 fold jobs in parallel (ConMin raw k ∈ {1,2,3,5} from one Stage-1, QuAcq-ex, scoring).
  Committed `total_ms` implies ~1,000 min per fold, but on REAL-FM-4 the same raw re-run was
  4–20× faster than its committed `total_ms` — time one fold first if CPU is shared
  (`--es ff` alone, `--workers 3`).

## 2. Gate and measures

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reproduction_gate busybox-1.18.0   # must report 0 mismatches
# add 'busybox-1.18.0' to KBS in apps/conmin_r1/__init__.py, then:
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.semantic_tier_corrected
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.solution_set_model_counting count busybox-1.18.0   # 854 vars; feasibility untested
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.solution_set_model_counting aggregate
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.cover_share_and_exact_equiv
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.solution_set_distribution
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.consistency_check <extracted feat/sosym-r1 tree>
```
