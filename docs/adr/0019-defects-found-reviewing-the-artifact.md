# ADR-0019 — Defects found while reviewing the public artifact

**Status:** Accepted. The first is fixed here; the other two are recorded rather than
fixed, deliberately.
**Date:** 2026-09-04, extended 2026-09-05.

All three were found while reviewing the public evaluation artifact. They are ordered by
severity, and the ordering is the point: the first returned a wrong answer without saying
so, while the other two produce only cosmetic differences. That is why the first was
worth fixing before submission and the others were not.

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
executable claim and nothing was executing it. It costs about one second.

## 2. `run_compare` config mode writes back into `kb_dir`

`apps/run_compare.py:223` writes each fold's evaluation into the CV file named by
`kb_dir`. In config mode that is the *input* file, so pointing it at a committed results
tree re-scores that tree in place.

This constrains the recipe rather than forbidding config mode: aimed at a scratch copy,
writing back is exactly the desired behaviour, and it is the only entry point that scores
a CV file correctly. Aimed at a committed tree it would re-score those results in place.
An earlier reading of this defect treated it as a reason to avoid config mode entirely,
which is how defect 1 above reached the README.

Not fixed because the behaviour is relied upon by the existing scoring workflow, and
changing where it writes is a contract change rather than a bug fix.

## 3. Scored-JSON byte layout depends on `PYTHONHASHSEED`

The scorer's output order is not deterministic across processes. The *values* are —
learned KB, accuracy, negative examples, metrics, summary all reproduce exactly — but
element order within a result varies, so two runs of the same scoring produce
byte-different files.

**Not fixed, and the reason is the cost of fixing it now.** Sorting the output changes
the byte content of every scored JSON, which changes every generated table, which means
the 93 assertions in `apps/sosym_r1/check_paper_numbers.py` have to be re-derived from
scratch. Close to a submission deadline that is a bad trade: the numbers are correct
today, and the change would put every one of them back in question to gain a property
nothing currently depends on.

The artifact's README states the limit plainly, so a reviewer who re-runs the scoring
and sees different bytes knows that is expected rather than a discrepancy.

Revisit after the deadline. If the sort lands, re-derive the assertions in the same
commit, and re-run the full acceptance rather than trusting that only ordering moved.
