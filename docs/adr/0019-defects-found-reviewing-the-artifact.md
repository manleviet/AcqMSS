# ADR-0019 — Defects found while reviewing the public artifact

**Status:** Accepted. The first is fixed here; the other three are recorded rather than
fixed, deliberately.
**Date:** 2026-09-04, extended 2026-09-05.

All four were found while reviewing the public evaluation artifact. They are ordered by
severity, and the ordering is the point: the first two return wrong answers without
saying so, while the last two produce only cosmetic differences. That is why the first
was worth fixing before submission and the rest were not.

## 1. `--kb` CLI mode silently scored an empty knowledge base for a CV file — FIXED

`apps/run_compare.py`'s CLI mode reads the single-knowledge-base schema, which expects
`kb_constraints` at the top level. A cross-validation file does not have that: its
constraints live inside `folds[]`. Handed a CV file, CLI mode finds nothing, scores an
empty knowledge base, and writes `n_kb: 0` with precision and recall `0.0` for all three
strategies. It exits `0`, prints `Done.`, and warns about nothing.

Measured on 2026-09-05 against a clean clone of the published artifact, following the
README as it then stood:

| via | n_kb | semantic F1, folds 0/1/2 |
|---|---|---|
| `--kb` CLI mode | 0 | 0.0000, 0.0000, 0.0000 |
| config mode, `kb_dir` at the scratch copy | 16 | 0.8462, 0.8462, 0.8627 |
| committed `data/results_sosym_r1/congen/` | 16 | 0.8462, 0.8462, 0.8627 |

**This is the worst failure shape an evaluation artifact can have.** It does not break;
it quietly reports that the paper's method learned nothing. A reviewer following the
instructions exactly would have concluded ConGen acquires zero constraints, and every
signal available to them — exit code, log output, a well-formed JSON — would have agreed.

**Fixed in `compare_kb`:** a file with no `kb_constraints` at the top level is now
refused with an explanation and exit 1, instead of scored as empty. Refusing to answer is
correct; answering zero is not.

The location is a hard constraint, not a preference. The check does **not** belong in
`ConGenResultData.from_json`, which is a loader that several tests require to parse every
recorded result without raising — `tests/test_t9_metrics_safety_net.py:171` calls it with
`# must not raise`, and `test_evaluation.py` calls it in four places. Refusing at the
loader would forbid reading a CV file at all. Refusing at this entry point rejects only
the combination that cannot work.

The change can only add a failure, never alter a correct answer: measured across `data/`,
214 files carry `kb_constraints` at the root and are scored correctly by this path, 274
are CV files that reach it only by mistake, and no test calls `compare_kb` or
`run_cli_mode` at all. A run that produced a right answer necessarily had the key.

`reproduce_tables_sosym.sh` now also runs the README's worked example and compares `n_kb`
and all three F1 values against the committed result, because a documented recipe is an
executable claim and nothing was executing it. It costs about 0.4 s, the median of three clean runs.

**One rough edge left in the message, deliberately.** It derives the config name from the
parent directory, because `make_score_configs` selects by that name and writes
`score_<name>.toml`. For a CV file kept somewhere else — `scratch/mycell/` — both printed
commands fail with "no CV files matched", so the message now states that the file must
sit in a directory called `congen` or `interactive`.

This was found as the third instance of one class, not as a case: **every command an
error branch prints must run verbatim, for every input shape that reaches that branch.**
Enumerating the shipped tree against that invariant found 6 sites printing a command and
2 that could not run — this one, and an install hint naming a sibling checkout the
artifact does not have. Both are fixed.

The better design is for `make_score_configs` to read the algorithm from the JSON instead
of inferring it from a path. That is deferred: it is roughly twenty lines of new code at
the end of a release, against one sentence of documentation, and the measured defect rate
through this review has been about one per forty-five lines written. Post-submission work,
along with defects 2, 3 and 4.

## 2. Partial resume reuses work from a different configuration

`apps/run_cv.py` skips any fold whose partial already exists, so a second run into the
same output directory reuses the first run's folds. A partial records `schema`, `model`,
`algorithm`, `solver_mode`, `query_mode`, `n_folds`, `fold_index`, `commit` and `fold` --
and neither `seed` nor `shuffle_bias`. **A partial produced by a different configuration
is therefore indistinguishable from a correct one**, and gets silently reused.

Reproduced end to end, through supported entry points, with no file edited by hand:

1. run the REAL-FM-7 cell with `shuffle_bias = false` into `scratch/` — KB `[13, 15, 16]`
2. run the README's cell (`shuffle_bias = true`) into the same `scratch/`, without
   clearing it
3. score and compare against the committed result

| fold | reused partials | committed reference |
|---|---|---|
| 0 | n_kb 13, F1 0.3846 / 0.6957 / 0.8462 | n_kb 16, F1 0.2069 / 0.6222 / 0.8462 |
| 1 | n_kb 15, F1 0.2857 / 0.6222 / 0.8077 | n_kb 16, F1 0.0690 / 0.4762 / 0.8462 |
| 2 | n_kb 16, F1 0.4828 / 0.7083 / 0.8302 | n_kb 16, F1 0.4138 / 0.6957 / 0.8627 |

Three wrong numbers that all look perfectly plausible. Nothing warns.

**`seed` is not the knob here, and that cost time on both sides of the review.** Measured:
`seed = 42` and `seed = 99` both give `[16, 16, 16]`; `shuffle_bias = false` gives
`[13, 15, 16]`. The seed does not change the learned knowledge base.

**Worked around, not fixed.** `reproduce_tables_sosym.sh` clears `scratch/congen` before
running the worked example, so the gate measures the current code rather than whatever is
on disk. That protects the gate, not a reader who reuses an output directory by hand.

The fix is for a partial to record the configuration that produced it — at minimum `seed`
and `shuffle_bias` — and for resume to refuse a partial whose configuration differs.
Deferred because it changes the on-disk partial schema, which is not a change to make in
the days before a submission.

## 3. `run_compare` config mode writes back into `kb_dir`

`apps/run_compare.py:231` writes each fold's evaluation into the CV file named by
`kb_dir`. In config mode that is the *input* file, so pointing it at a committed results
tree re-scores that tree in place.

This constrains the recipe rather than forbidding config mode: aimed at a scratch copy,
writing back is exactly the desired behaviour, and it is the only entry point that scores
a CV file correctly. Aimed at a committed tree it would re-score those results in place.
An earlier reading of this defect treated it as a reason to avoid config mode entirely,
which is how defect 1 above reached the README.

Not fixed because the behaviour is relied upon by the existing scoring workflow, and
changing where it writes is a contract change rather than a bug fix.

## 4. Scored-JSON byte layout depends on `PYTHONHASHSEED`

The scorer's output order is not deterministic across processes. The *values* are —
learned KB, accuracy, negative examples, metrics, summary all reproduce exactly — but
element order within a result varies, so two runs of the same scoring produce
byte-different files.

**Not fixed. The reason recorded here has now been wrong twice, and that is worth more
than the decision it was defending.**

*First reason, false:* that sorting the output would change every generated table and
force all 93 assertions to be re-derived. `apps/extract_results.py:656` builds each row
from `fs['tp'] + fs['fn']`, `fs['tp']`, `fs['fp']`, `fs['fn']` and the three metric
values — counts and numbers, not element sequences — and every loop reaching them is a
`sorted()`. Element order reaches no table cell.

*Second reason, also false:* that nothing short of a full re-run could establish that
only ordering had moved, "which is the one thing a byte diff cannot show". A canonical
comparison shows exactly that. Measured: the same cell scored under `PYTHONHASHSEED=0`
and `PYTHONHASHSEED=12345` is byte-different and **canonical-equal** — sort the keys,
sort the lists, compare — in well under a second per file.

*The honest reason, which was available both times:* **nothing depends on the ordering,
and committed evidence does not get rewritten days before a submission.** The fix would
rewrite every scored JSON in both trees to buy a property no consumer uses. The cost is
ordinary — re-scoring one 28-file tree measures 20.6 s, so both trees are minutes, and
the canonical diff that verifies the result is instant. It is a small job being deferred
because it is unnecessary now, not a large one being avoided.

**The meta-lesson is the reusable part.** Both wrong reasons were produced while
justifying a decision that had already been made, and both reached for the most
impressive-sounding cost available — "93 assertions", then "unverifiable" — when a
smaller true reason was sitting in plain view. Neither was checked against the code until
someone went looking. A decision defended by a false reason survives only until the
reason is tested, and then the decision is doubted along with it.

Revisit after the deadline. Verify with a canonical comparison, which is what actually
answers the question, and do not expect the tables to move — on the evidence above they
will not.
