# Step 0 gate — fold-level granularity and resume

Branch `feat/sosym-r1`, code commit `3f6ce91` (parent `590febe`).
Measured 2026-08-23. Environment: flamapy-fm / -fw / -sat `2.6.0.dev4`,
flamapy-bdd `2.0.1` (the known-red `pip check`, normal working state),
canonical `../explanation` editable at `0.1.0` (`275 passed`), Python `3.11.14`.
Suite **673 passed, 1 skipped** (666 + the 7 tests added here).
`git status --porcelain data/results/` empty before and after every run; every
run used `-o <scratch>`.

## What was built

`run_cv.py` gains `--folds 0,2` and `--merge-only`. Each fold is written to
`<out>/<algorithm>/partials/{name}_{mode}[_{query_mode}]_fold{i}.json` the moment
it finishes, and a later call restores whatever is on disk and computes only the
rest. `_run_cv_loop` was split into `_compute_fold` (one fold, reads only
`fold_data` and its index) and `_assemble_cv_result` (every cross-fold artifact:
accuracy mean/std, intersected KB, aggregated performance). Merged folds and
single-process folds go through the same assemble and the same
`generate_unified_cv_dict`, so the paths agree by construction.

Deviation from the handoff's filename: `query_mode` is in the partial name for
the interactive algorithm, mirroring the final CV filename. Without it
`example_only` and `example_first` share an output directory and would resume
from each other's folds. Verified distinct on disk.

## Step 0b — falsification, not inspection

**The assertion had to be built before it could be used.** "Byte-identical" fails
between two *identical monolithic runs*, so asserting it would have failed for
the wrong reason. Measured the baseline first: two monolithic ConGen runs of
REAL-FM-7 rs_1n differ in **133 leaves across 63 distinct paths, every one a
timer, and zero non-timing paths**. Interactive: 181 leaves, 83 paths, zero
non-timing. That measured set defines the exclusion; anything outside it is real.

| Test | Result |
|---|---|
| ConGen: 3 single-fold **processes** (order 2,0,1) vs monolithic | **0 semantic diffs** |
| ConGen: `--folds 1,2` then `--folds 0` vs monolithic | **0 semantic diffs** |
| Interactive: 3 single-fold **processes** (order 2,0,1) vs monolithic | **0 semantic diffs** |
| Mutation: fold 2's partial replaced by fold 0's payload | **52 semantic diffs — detected** |

The fold-order tests matter beyond the handoff's argument, which covers the data
dependence but not the `runner`: `_run_cv_loop` builds one runner and calls
`run()` per fold, and QuAcq additionally shares `self.oracle` and queries it.
Running the folds out of order, in and across processes, is what actually
falsifies cross-fold state. It found none.

## Step 0c — the unseeded pool

`n_fold_cross_validation_interactive` now refuses `shuffle_bias=false`.
`cross_validation.py:207` passes `None` as the per-fold seed when the knob is
off, and `query_provider.py:60` takes it straight into `random.Random(seed)`, so
the pool order — and therefore which queries are asked, and therefore the learned
KB — would come from OS entropy with nothing reporting it. `run_cv` also exits
early with the same message. ADR-0015's decoupling is *not* implemented here.

## Step 0d — every test shown able to fail

Seven mutations run against the seven new tests. Six were caught immediately.
**One survived and exposed a real gap**: forcing `missing = []` in `_run_cv_loop`
makes a half-finished window assemble anyway, emitting a CV JSON with the
ordinary name and shape whose mean, std and intersected KB were computed over a
*subset of folds* — indistinguishable downstream from a complete run. Added
`test_a_window_that_ends_early_writes_no_cv_result`, which asserts the file is
**absent**; re-mutated, now caught.

## Finding that changes step 1: memory is a function of process position

`memory_peak_mb` is reported (Tables 7–8). It is **not** a function of the fold's
computation. `tracemalloc` peak depends on where the fold sits in its process:

| condition | fold 0 | fold 1 | fold 2 |
|---|---|---|---|
| ConGen, one process | 0.353140 | 0.303332 | 0.301287 |
| ConGen, three processes | 0.353140 | **0.370357** | **0.370357** |
| ConGen, `[1,2]` then `[0]` | 0.353140 | **0.370357** | 0.301432 |
| Interactive, one process | 1.934213 | 1.889734 | 2.030039 |
| Interactive, three processes | 1.934213 | 2.032121 | 2.172715 |

Fold 0 is identical everywhere — it is always first in its process. A fold that
runs first in a fresh process reports the *same* peak regardless of which fold it
is; a fold running second reuses warm allocations and reports ~20 % less. It is
deterministic given (fold, position-in-process), so it is not noise — it is a
systematic offset keyed to execution shape.

Consequence for the sweep: busybox `ff` (11.4 h) and REAL-FM-4 `rs_3n` (12.5 h)
**must** split across windows, while REAL-FM-7, fqa and arcade fit in one run. If
the runner is free to batch folds, memory becomes incomparable between the small
KBs and the large ones — a scale claim contaminated by scheduling.

**Recommendation: one fold per process, uniformly, for every cell.** The sweep
runner should invoke `run_cv` once per fold and never pass `--folds 0,1`. Cost is
one interpreter start (~0.5 s) per fold against units measured in hours. This is
also the finest-grained unit for the budget check, so it costs nothing there.

## Open questions

1. **QuAcq's wall-clock timeout does not exist on the path §7 C1 decision 5
   needs.** `QuAcqRunner.__init__` takes `timeout_s`, but its docstring says
   "Example modes ignore it", `_run_example_mode` never passes a deadline, and
   `n_fold_cross_validation_interactive` never plumbs it. So "5,000 queries + a
   wall-clock timeout" is today 5,000 queries only. Confirm whether step 4 should
   implement the deadline on the example path, or whether the cap alone suffices
   given `convergence_reason` is now serialized.
2. **`total_runtime_ms` on a merged result** is the sum of the wall-clock of the
   calls that produced the folds, so across windows it excludes idle time and is
   not the same quantity as a monolithic run's. It sits inside the excluded
   timing set. Confirm nothing in the tables reads it.
3. **`-o` is still optional.** The handoff calls passing it non-negotiable and the
   failure silent. A `--allow-default-output` opt-in would make it loud, but it
   changes a CLI contract C2 depends on, so it is left alone pending a decision.
