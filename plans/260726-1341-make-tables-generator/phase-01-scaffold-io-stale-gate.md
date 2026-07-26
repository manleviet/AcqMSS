---
phase: 1
title: Scaffold + IO + stale gate
status: completed
effort: ~2h
priority: P1
dependencies: []
---

# Phase 1: Scaffold, CSV IO, STALE INPUT + empty-scope gates

## Overview
Stand up `apps/make_tables` (package), the CLI, the per-KB `_long.csv` loader, and the two gates that must run BEFORE any table is produced (v2 STALE INPUT + G3 empty-scope). No tables yet.

## Architecture
- **Package** `apps/make_tables/`: `__main__.py` (CLI), `loader.py` (CSV read + union), `gates.py` (stale + empty-scope), `provenance.py` (skeleton). CLI stays `python -m apps.make_tables` (Open Q1 — file→package deviation from spec's literal `apps/make_tables.py`; functionally identical).
- **CLI (v1 + red-team #10):** `python -m apps.make_tables [--tables-dir DIR] [--official] [--exclude-2cov/--no-exclude-2cov] [--kbs REAL-FM-7 …] [--results-dir data/results_conmin]`. Default `--exclude-2cov` ON. **Default `--tables-dir` = a throwaway path (`/tmp/make_tables_out`), NOT the production dir** — writing canonical `data/results_conmin/tables/` requires explicit `--official` (which additionally asserts the sweep is complete/merged). Prevents the bare acceptance-criterion invocation from landing mid-sweep tables in the official location.
- **Loader (red-team #5, #12, #13):** read per-KB `{KB}_long.csv` for the 5 fixed KBs; **prefer per-KB over merged** `conmin_eval_long.csv`. *Correct grounding:* per-KB = **61 cols** (all 40+ spec cols present); merged = **56 cols**; the delta is the **5 `quacq_*` counter columns** — that (not a col count) is why merged is stale (also lacks QuAcq-active + has blank `convergence_reason`). Union rows by `(kb, example_set, fold, condition, negatives, k)`. **A KB with no file / missing rows → its cells `--` (derive `--` from row-presence, NOT from a hardcoded coverage snapshot — REAL-FM-4 is ~complete now).** **Atomic read (sweep is live, `_long.csv` is written non-atomically — `run_conmin_eval.py:44` `open(w)`, unlike the atomic JSON):** snapshot mtime → copy/read → re-check mtime; if changed, retry; a mid-file csv parse error ⇒ treat that KB as "not ready → `--`", never crash. pandas if available; else stdlib `csv`.

## STALE INPUT gate (v2) — PER-KB, not global (red-team #7)
Refuse to silently produce tables on pre-fix input, but scope the refusal **per KB** so one stale/torn KB does not deny the fresh KBs the paper needs. For each loaded KB, mark STALE if:
- a `QuAcq` or `QuAcq-active` row has **blank** `convergence_reason`, OR
- the `quacq_*` counter columns are **absent** from that KB's header.
A STALE KB → its cells forced to `--` with a prominent per-KB `STALE INPUT: <KB>` banner; **global abort only if ZERO KBs survive**. (This composes with the loader's torn-read → `--`.) The blank-`convergence_reason` on A/C/C∪S rows is expected and ignored (gate applies to QuAcq/QuAcq-active only).

## Empty-scope gate (v2 G3)
Print `quacq_empty_scope_appends` per KB **even when 0**. If **non-zero on REAL-FM-4 or busybox** → print that the sweep-wide "precision 1.000" claim is unavailable, stop, and flag for CW Impl → CW Main. (Absent column ⇒ pre-counter row ⇒ `--`, never `0`.) Today it is 0 on all loaded KBs → the stop-path must be exercised by a fixture, not real data.

## PROVENANCE skeleton
`provenance.py` collects: source file paths + **mtimes** + `git rev-parse HEAD`; per-table filter + row counts get appended in Phase 3/4 → `tables/PROVENANCE.md`.

## Related Code Files
- Create: `apps/make_tables/{__init__.py,__main__.py,loader.py,gates.py,provenance.py}`
- Read-only: `data/results_conmin/*_long.csv`, `apps/run_conmin_eval.py` (column provenance)

## Implementation Steps
1. Package skeleton + argparse CLI (defaults per v1); wire `setup_logging` like sibling apps (stderr diagnostics, stdout = product).
2. `loader.load_long(results_dir, kbs)` → dict/DataFrame keyed by the 6-tuple; prefer per-KB.
3. `gates.check_stale(...)` + `gates.check_empty_scope(...)`; call both before anything else in `__main__`.
4. `provenance.collect(source_files)` → mtimes + git SHA.
5. `--kbs`/`--tables-dir`/`--exclude-2cov` plumbed through.

## Success Criteria
- [ ] `--help` shows the CLI; `--exclude-2cov` default on; **default `--tables-dir` is throwaway**; `--official` required for canonical dir.
- [ ] Loader unions per-KB rows by the 6-tuple; prefers per-KB; missing rows → `--` (derived, not hardcoded); **torn-read guard** (mtime snapshot/retry) → in-flight KB → `--` not crash.
- [ ] **Per-KB** STALE gate: stale KB → `--`+banner; fresh KBs still emit; global abort only if zero survive (fixture-tested both ways).
- [ ] Empty-scope value printed per KB; non-zero → stop path exercised (fixture, since real data is 0).
- [ ] PROVENANCE captures source mtimes + git SHA + **real** header length (programmatic, not hand-typed).

## Risk Assessment
- Risk: pandas not a direct dep. Mitigation: confirm import; fall back to stdlib `csv` + manual grouping (61 cols is fine).
- Risk: package vs file (Open Q1). Mitigation: confirm with user; either way CLI unchanged.
