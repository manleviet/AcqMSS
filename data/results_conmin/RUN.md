# ConMin comparison eval — sweep runbook

Staging-safe: each `--kb X` run writes **`X_long.csv` + `X_cv.csv`** (per-KB), never the
shared file, so KBs run in any order / in parallel without clobbering. Consolidate at the
end with `--merge`. Config: `apps/conf_conmin/run_conmin_eval_config.toml`. Folds are
pre-recorded (`data/folds/`) — seed is fixed; nothing is regenerated.

> ⚠ Stale artifacts: any `conmin_eval_{long,cv}.csv` already in this dir is from a
> pre-fix schema (older columns). Re-run REAL-FM-7 (fast) with the current code, then
> `--merge` overwrites them. `--merge` ignores `conmin_eval_*.csv` in its glob, so it is
> idempotent and never folds a stale merged file back in.

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

Rough wall-clock (unmeasured; dominated by the **QuAcq** reference — 3 folds × 6
example-sets × |B|; ConMin's own A/C/C∪S k-sweep is comparatively cheap):

| KB | #feat | \|B\| | rough estimate |
|---|---|---|---|
| REAL-FM-7 | 14 | 295 | ~1–3 min |
| fqa | 179 | 459 | ~10–30 min |
| arcade-game | 65 | 1,755 | ~20–60 min |
| REAL-FM-4 | 291 | 2,079 | ~1–3 h |
| busybox-1.18.0 | 854 | 6,635 | **many hours** — run last, alone |

Subset a heavy KB for a first pass if needed, e.g. `--example-sets rs_1n rs_3n 2cov ff`
(flag the deferred example-sets in the run report).

## Consolidate (after all KBs finish)

```bash
python -m apps.run_conmin_eval $CFG --merge -v      # → conmin_eval_{long,cv}.csv
```

`conmin_eval_long.csv` (one row per KB × example-set × condition × k × negatives) and
`conmin_eval_cv.csv` (3-fold mean±std) are the source of truth for the 9 paper tables.

## Outputs per KB
- `{kb}_{es}_eval.json` — per-(KB,example-set): raw rows + CV aggregate + provenance note.
- `{kb}_long.csv` / `{kb}_cv.csv` — per-KB long/tidy + CV.
- (after merge) `conmin_eval_long.csv` / `conmin_eval_cv.csv` — all KBs.
