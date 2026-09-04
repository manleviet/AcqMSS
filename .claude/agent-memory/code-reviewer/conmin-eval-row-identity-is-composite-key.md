---
name: conmin-eval-row-identity-is-composite-key
description: ConMin eval JSON rows are keyed by (condition,k,negatives) not condition alone — any surgical merge/replace must match the full tuple
metadata:
  type: project
---

In the ConMin eval pipeline (`conacq/eval/conmin_cv_evaluator.py`, `apps/run_conmin_eval.py`),
each per-(KB,example-set) JSON `rows` entry is identified by the COMPOSITE key
`(condition, k, negatives)` — and `aggregate_cv` groups on `(kb, example_set, negatives, condition, k)`.
A single `condition` label (e.g. `C∪S`) maps to MANY rows: k∈{1,2,3,5} × neg∈{reduced,raw} × folds.

**Why:** any "replace the rows for condition X" operation (the `--conditions` surgical merge)
that filters `preserved` by `condition` alone will delete ALL k/negatives rows for that condition,
then re-emit only the ones the current run's `--k`/`--negatives`/config produce. If the recompute
uses a narrower k or negatives set (CLI flag or config drift) than the original full run, the
omitted rows are silently lost and `aggregated` is recomputed without them.

**How to apply:** when reviewing any merge/dedup/replace over these eval JSONs, verify the match/replace
key is the full `(condition,k,negatives)` tuple (or that the run's k/negatives are pinned to the
existing file's), not `condition`. Same trap applies to QuAcq-active provenance (`qa_max_queries`/
`qa_timeout_s`) which the `--merge` path already guards per (kb,es). See [[golden-recorded-from-old-code]]
for the sibling anti-tautology lesson on verifying refactors by substitution.
