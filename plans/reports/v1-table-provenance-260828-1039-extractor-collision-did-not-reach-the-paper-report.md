# Did the extractor's method collision corrupt a published number?

Date 2026-08-28. Branch `feat/sosym-r1`. Question: `apps/extract_results.py` collapsed
ConGen, QuAcq example-only and QuAcq example-first onto one key. The defect predates the
submission, and Tables 13/14 are exactly the tables that compare the two query modes. So
is a published figure the wrong mode's number, rather than merely stale?

**Answer: no. The defective path contributed nothing to the paper.** Reading only; no
committed data was written.

## The defect is real and predates submission

`git show 0b0313a:apps/extract_results.py:93` carries the non-capturing suffix group, so
at the submitted commit the three methods parsed identically. Simulating the submitted
loader over the committed `data/results/interactive/` (36 files, unsorted `glob`, exactly
as the old loader iterated):

| | |
|---|---|
| files parsed | 36 |
| distinct keys | **18** |
| silently discarded | **18** |
| surviving method | 12 `example_first`, 6 `example_only` — **mixed**, varying cell by cell |

Within REAL-FM-7 alone: `2cov`, `ff`, `rs_1n`, `rs_m` kept example-only; `rs_2n`, `rs_3n`
kept example-first. Filesystem order, not a choice.

## But it never reached the paper — two independent reasons

**1. The published mode-split tables are not extractor output.** `evaluation.tex` builds
them from row groups — `\multicolumn{5}{l}{\textit{Iterative -- example-only}}` at lines
339 / 368 / 410 and the example-first counterparts. Nothing in the repo emits that
structure: `grep -rl "Iterative -- example" apps/ tools/` returns nothing. A collapsed
load cannot produce a table that distinguishes the two modes, and these do; they were
assembled by a route outside the repo.

**2. The extractor's committed output has no incremental data at all.**
`paper/tables/results_tables.tex` (untracked, written 2026-07-17):

| tables | rows with data |
|---|---|
| every **incremental** table | **0** |
| every **non-incremental** table | full |

Every file in `data/results/interactive/` is `_cv_incremental_*`. The interactive side of
that artefact is empty, so the files the defect would have collapsed contributed nothing
to it.

## The cause of the empty half is a live forward risk

`data/results/` holds `congen/`, `interactive/`, `old_results/` and **no top-level CV
files**. The loader globbed `results_dir.glob('*_cv_*.json')` — flat, non-recursive — so
the documented `--results-dir data/results` matched nothing and rendered a full set of
tables with `-` in every cell, silently. That is what shipped.

`data/results_sosym` has the same shape: **0** top-level CV files. Pointing the extractor
at it would have repeated the outcome exactly, on the revision's own data.

Fixed, with both halves falsified:

- the glob now searches the algorithm subdirectories as well as the flat level —
  `data/results_sosym` goes from **0 entries to 78**;
- an empty load is refused rather than rendered: it logs the cause, writes no file, and
  **exits 1** (previously `main()`'s status was discarded at the `__main__` guard, so even
  an explicit refusal would have exited 0 — the same silent-success shape).

## What this changes

Nothing for N10's disclosure: no published number is the wrong mode's. The provenance
statement gains a sentence — the SoSyM chain `run_cv → run_compare → extract_results →
paper/tables/` was never exercised end to end for v1; the comparison tables came from
another route, and the extractor's committed output is empty on the incremental half.

## Unresolved

1. The route that produced Tables 13/14 is outside the repo and unidentified beyond "not
   `extract_results.py`". If the revision regenerates them from the repo, that route is
   replaced rather than reproduced.
2. `paper/tables/` is untracked, so the artefact carries no provenance of its own.
