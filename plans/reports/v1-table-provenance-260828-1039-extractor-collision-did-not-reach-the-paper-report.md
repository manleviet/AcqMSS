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

**1. The published mode-split tables are not extractor output.** They are built from
hand-written row groups — `\multicolumn{5}{l}{\textit{Iterative -- example-only}}` and its
example-first counterpart — in `tab:iterative_accuracy` and `tab:iterative_semantic`.
Nothing in this repo emits that structure: `grep -rl "Iterative -- example" apps/ tools/`
returns nothing, and that half of the argument is tracked code. A collapsed load cannot
produce a table distinguishing the two modes, and these do.

*Source discipline.* The local `paper/evaluation.tex` shows the same row groups, but
`paper/` has **0 tracked files**, so it cannot corroborate anything about the past — it is
a working-tree artefact of unknown age. The citation of record is
`Overleaf/SoSyM/main-r1.tex`, which is tracked in the manuscript repository; that tree is
not reachable from this machine, so it is recorded on Viet-Man's attestation rather than
verified here.

**2. The extractor's own output has no incremental data at all.**
`paper/tables/results_tables.tex` — **untracked**, written 2026-07-17, so this is an
observation about the working tree and carries no history of its own:

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

## An exit status that reports success while refusing

Worth naming on its own. `main()` returned non-zero on the refusal and the `__main__`
guard discarded it, so an explicit, logged refusal exited **0**. Every wrapper, `&&`
chain and CI step downstream reads that as success.

It is the same family as `missing = []`, the truthiness filter, the hollow guard test and
`--diff-filter=D`: a failure that cannot be observed by the thing downstream of it. This
instance is the worst of them, because the exit code is the channel the other fixes rely
on to be noticed — a guard that cannot report its own refusal disarms every guard behind
it.

## What this changes for N10

No published number is the wrong mode's, and staleness is not the sharp end. Both
`paper/tables/` and `paper/evaluation.tex` are untracked: **the published tables have no
provenance in the repository at all**, and the route that produced them is not recorded
anywhere we ship. That is what a reproducibility statement has to say, and it is more
uncomfortable than "the numbers are stale".

The honest positive belongs in the same paragraph. The revision is the first version in
which the documented pipeline actually produces the tables: `run_cv → run_compare →
extract_results → paper/tables/` now runs end to end on the revision's own data, refuses
loudly when it loads nothing, and exits non-zero when it refuses. That is a real
improvement to disclose, not a caveat to bury.

## Unresolved

1. The route that produced Tables 13/14 is outside the repo and unidentified beyond "not
   `extract_results.py`". If the revision regenerates them from the repo, that route is
   replaced rather than reproduced.
2. `paper/tables/` is untracked, so the artefact carries no provenance of its own.
