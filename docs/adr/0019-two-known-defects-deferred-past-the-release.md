# ADR-0019 — Two known defects, deferred past the release

**Status:** Accepted. Recorded rather than fixed, deliberately.
**Date:** 2026-09-04

Both were found while reviewing the public evaluation artifact. Neither is fixed here,
and the reason differs for each.

## 1. `run_compare` config mode writes back into `kb_dir`

`apps/run_compare.py:223` writes each fold's evaluation into the CV file named by
`kb_dir`. In config mode that is the *input* file, so pointing it at a committed results
tree re-scores that tree in place.

This is why the artifact's README tells a reader to use CLI mode for a newly produced
fold: the config-mode recipe would silently re-score the 28 committed results and never
touch the new one.

Not fixed because the behaviour is relied upon by the existing scoring workflow, and
changing where it writes is a contract change rather than a bug fix.

## 2. Scored-JSON byte layout depends on `PYTHONHASHSEED`

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
