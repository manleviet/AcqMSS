# ConMin comparison eval — sweep runbook

## TL;DR — reproducing the paper's tables

One command, from the repo root. Every step is gated; it stops at the first failure
and names it, and it never emits tables from inputs it could not verify.

```bash
./reproduce_tables.sh          # from the committed per-KB CSVs        (~1 min)
./reproduce_tables.sh --draft  # same tables, written to /tmp instead  (~1 min)
./reproduce_tables.sh --full   # re-run the whole sweep first          (~12+ h)
```

⛔ **`--full` is for reproducing from scratch, not for refreshing.** $KB_5$ (busybox)
QuAcq-active ends on a **wall-clock timeout**, not on the deterministic query rail —
its 1,901 queries are what one machine reached in 36,000 s, which is why it is the
sole member of `NON_ANCHORABLE_QUACQ_ACTIVE`. A re-run produces a **different**
$KB_5$ row and silently invalidates every $KB_5$ figure in the paper. Regenerate
only when the **data** or the **generator** changed.

`--draft` and the default differ **only in output directory** — same inputs, same
generator, numerically identical tables. Use `--draft` to test a change to the
pipeline without overwriting the committed `tables/`; it does not exercise the
`--official` code path, so follow a draft run with one official run and check that
the only diff is `PROVENANCE.md`'s SHA line.

Chain: **environment** → sweep (skipped unless `--full`) → **freshness gate** →
`--merge` → `make_tables --official` → **verify**. Output lands in
`data/results_conmin/tables/` (11 `.tex` + `.md`, `exact-equiv.md`, `PROVENANCE.md`).

The verify step enforces three things the rest of this file assumes:

1. `PROVENANCE.md`'s git SHA is **not** `-dirty` — the recorded commit must name the
   code that produced the tables, never a commit that merely happened to be HEAD.
   (This is why the order is *commit the generator → regenerate → commit the tables*;
   a SHA can never name the commit that contains its own artifact.)
2. at least 11 `.tex` tables were emitted and the self-check did not fail;
3. no generated artifact contains a hard-coded percentage or a plan word
   (`pending`, `tonight`, …) — a caption that quantifies the data must be **derived
   from the data**, and an artifact states the state at generation time, never a plan.

Copying the tables into the paper is deliberately **not** automated — nothing in this
repo ever writes `Overleaf/`:

```bash
cp data/results_conmin/tables/*.tex Overleaf/AAAI/tables/ && ./sync.sh AAAI push
```

The sections below document the individual stages, for staged or partial runs.

---

Staging-safe: each `--kb X` run writes **`X_long.csv` + `X_cv.csv`** (per-KB) plus a
per-example-set **`X_{es}_eval.json`**, never the shared file, so KBs run in any order /
in parallel without clobbering. `--merge` consolidates from the **per-example-set JSONs**
(the atomic unit — never clobbered), so a KB re-run with a *different* `--example-sets`
subset still keeps its earlier sets in the merge. Config:
`apps/conf_conmin/run_conmin_eval_config.toml`. Folds pre-recorded (`data/folds/`); seed
fixed; nothing regenerated.

**5 conditions now** — A / C / C∪S / **QuAcq** (passive, example-only) / **QuAcq-active**
(oracle-mode, self-generated queries vs the FM oracle). QuAcq-active is learned **once per KB**
(fold/example-independent) with a query budget (`quacq_active_max_queries`, deterministic rail)
and a wall-clock `quacq_active_timeout_s` safety net. New row columns: `convergence_reason`
(empty_bias/no_query/max_queries/timeout — blank for A/C/C∪S) and provenance `qa_max_queries`
/`qa_timeout_s`. A QuAcq-active fold whose reason is `timeout`/`max_queries` is **non-converged**
(partial theory) — `aggregate_cv` counts it (`n_timeout`/`n_maxq`/`n_nonconverged`) and excludes
it from the mean; report it "did not converge", never as a clean number. Disable with
`--no-quacq-active`; size a big KB with the config per-KB map or `--quacq-active-max-queries N`
(e.g. busybox needs a budget ≫ |B|=6635 to reach `empty_bias` rather than `max_queries`).
`--merge` tolerates the additive columns (won't false-warn against pre-column committed JSONs)
but warns on QuAcq-active **provenance conflicts** (a KB merged across passes with different
budget/timeout).

> ⚠ Stale artifacts: `data/results_conmin/` currently holds pre-fix-schema
> `conmin_eval_*.csv` + `REAL-FM-7_*_eval.json` (older columns). **Re-run REAL-FM-7 fully**
> (fast) to overwrite its stale JSONs, then `--merge`. `--merge` warns if it sees mixed
> column schemas (stale + fresh); if so, re-run the affected KB(s) fully. Best: delete the
> stale `conmin_eval_*.csv` + `REAL-FM-7_*_eval.json` before the sweep.

## Per-KB runs (light → heavy; nice + nohup + log)

```bash
CFG=apps/conf_conmin/run_conmin_eval_config.toml
OUT=data/results_conmin

# light — foreground is fine (~minutes)
python -m apps.run_conmin_eval $CFG --kb REAL-FM-7 -v            # 14 feat, |B|=295

# heavier — background each; watch the .log
nohup nice -n 10 python -m apps.run_conmin_eval $CFG --kb fqa            > $OUT/fqa.log            2>&1 &
nohup nice -n 10 python -m apps.run_conmin_eval $CFG --kb arcade-game    > $OUT/arcade-game.log    2>&1 &
nohup nice -n 10 python -m apps.run_conmin_eval $CFG --kb REAL-FM-4      > $OUT/REAL-FM-4.log      2>&1 &
nohup nice -n 10 python -m apps.run_conmin_eval $CFG --kb busybox-1.18.0 > $OUT/busybox-1.18.0.log 2>&1 &
```

## Recompute ONE condition (reuse Stage-1) — `--conditions`

To update only the QuAcq column (e.g. after a QuAcq fix) without re-running the expensive
ConMin Stage-1 (AdmPoolMSS): `--conditions quacq` (or `quacq,quacq-active`). It **surgically
merges** into the existing `{kb}_{es}_eval.json` — recomputes only the selected condition(s),
preserves every other condition's rows verbatim, recomputes `aggregated`. Measured Stage-1-skip
speedup ~1.9–2.8× (bigger on large |B|).
```bash
python -m apps.run_conmin_eval $CFG --kb REAL-FM-7 --conditions quacq
```
**Determinism:** QuAcq (both modes) is hash-seed-independent — FindScope iterates in canonical
(sorted) order, so results do NOT depend on `PYTHONHASHSEED` (verified across fixed seeds + unset
on REAL-FM-7/fqa/arcade-game/REAL-FM-4). No env pin needed; ConMin/A/C/C∪S are hash-independent.
**Canonical figures** (REAL-FM-7, glucose4): oracle-mode **KB=10, oracle_queries=342, no_query**.

**Threats to validity (report QuAcq numbers WITH these caveats):**
- *Solver-conditional.* The solver is pinned in config (`[general] solver_name = "glucose4"`) and
  feeds BOTH the ConMin checker and the QuAcq oracle/runner (one value, no confound). QuAcq is
  solver-sensitive: glucose4 → KB=10 on REAL-FM-7; another solver may differ by ±1 constraint
  (e.g. minisat → KB=9). Always report QuAcq with the solver named.
- *Order-dependent by design.* QuAcq's learned theory depends on the constraint-processing order —
  a known property of the algorithm, not a defect. We fix ONE canonical order (sorted-by-name), so
  `oracle_queries=342` is reproducible; a different canonical order would change the count. Handled
  by fixed order + 3-fold CV averaging + this disclosure — NOT by claiming order-invariance.

Rules: a full run must exist first (errors if `{kb}_{es}_eval.json` is missing — nothing to
reuse); do NOT combine `--conditions` with narrower `--k`/`--negatives` (it refuses rather than
drop existing rows); `quacq_query_mode` (config) selects example_only/example_first.
**Provenance caveat:** only recompute a condition onto a JSON produced by the SAME code version —
recomputing QuAcq (post-`is_valid`-fix semantics) onto a pre-fix full-run JSON silently mixes
semantics across conditions (no code-version guard). Safest: recompute onto a post-fix full run.

Rough wall-clock (unmeasured; dominated by the **QuAcq** reference — 3 folds × 6
example-sets × |B|; ConMin's own A/C/C∪S k-sweep is comparatively cheap):

| KB | #feat | \|B\| | rough estimate |
|---|---|---|---|
| REAL-FM-7 | 14 | 295 | ~1–3 min |
| fqa | 179 | 459 | ~10–30 min |
| arcade-game | 65 | 1,755 | ~20–60 min |
| REAL-FM-4 | 291 | 2,079 | ~1–3 h |
| busybox-1.18.0 | 854 | 6,635 | **many hours** — run last, alone |

Subset a heavy KB for a first pass if needed, e.g. `--example-sets rs_1n rs_3n 2cov ff`,
then a deferred pass `--example-sets rs_2n rs_m` — each example-set keeps its own JSON, so
`--merge` picks up both passes (flag the deferral in the run report anyway). **Safe only if the
QuAcq-active budget is consistent across the passes** for that KB (same `quacq_active_max_queries`
/`quacq_active_timeout_s`) — else `--merge` warns on a provenance conflict (the two passes learned
different theories under one `QuAcq-active` label). Keep the per-KB budget fixed for a KB.

## Consolidate (after all KBs finish)

> Prefer `./reproduce_tables.sh` (see the TL;DR at the top) — it runs the freshness
> gate before this step, checks the merge log for provenance conflicts, and continues
> on to the tables. The bare command below is for staged or partial runs.

```bash
PYTHONPATH=. python3 freshness_gate.py              # MUST exit 0 before merging
python -m apps.run_conmin_eval $CFG --merge -v      # → conmin_eval_{long,cv}.csv
python -m apps.make_tables --official -v            # → tables/ + PROVENANCE.md
```

`conmin_eval_long.csv` (one row per KB × example-set × condition × k × negatives) and
`conmin_eval_cv.csv` (3-fold mean±std) are the source of truth for the 9 paper tables.

## Outputs per KB
- `{kb}_{es}_eval.json` — per-(KB,example-set): raw rows + CV aggregate + provenance note.
- `{kb}_long.csv` / `{kb}_cv.csv` — per-KB long/tidy + CV.
- (after merge) `conmin_eval_long.csv` / `conmin_eval_cv.csv` — all KBs.
