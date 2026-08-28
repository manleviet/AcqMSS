# CC → CW: what landed 2026-08-28, what is running, what is queued

Branch `feat/sosym-r1`. Queue below agreed by Viet-Man 2026-08-28 23:20.

## Landed — the fixes, at one code state

`faa00ef` lands all three negative-example fixes coupled with the repaired tests: the
negated form asserts the example instead of switching off its guard; the negatives are
passed to Reduce one per example rather than folded into one assumption; they are reduced
before the bias constraints. `c0f448f` re-baselines the five ConGen goldens, with the
confinement evidence — `n_bias`, `n_mss`, `bg_clauses`, every pinned count, the diagnosis
id layout and **both QuAcq entries byte-for-byte** held. Suite **683 passed, 1 skipped**;
baseline moved in CLAUDE.md at `0c4619d` with commit and environment.

**Attribution (`ee1fce6`).** (a)+(b) without the reduction-order change move **0 / 216**
tier metrics — the bias `kb_constraints` are identical to committed on **72/72 folds**.
All 155 moved metrics, max 0.0909, belong to the ordering change alone. So the two defect
fixes get the clean sentence, and the ordering change is the one carrying a number.

## Landed — the extractor, which had never produced a table

Three defects in `apps/extract_results.py`, found while implementing A5's decisions:

- `069f2c2` — semantic P/R/F1 and exact equivalence were absent. Two tables per decision
  (c); recall leads; equivalence computed in `run_compare` on the DELIVERED theory, with
  the two-object contract commented on both sides so the next reader does not "fix" the
  asymmetry.
- `2157122` — the filename parser discarded the query-mode suffix, so ConGen and both
  QuAcq modes shared one key and two were silently overwritten. Falsified on real files:
  3 in, 1 entry before, 3 after.
- `664f40b` — the glob was flat while the sweep writes `<results>/<algorithm>/`, so the
  documented path matched nothing and rendered a full set of tables with a dash in every
  cell. `data/results_sosym` went from **0 entries to 78**. An empty load is now refused
  and exits non-zero — the exit status was being discarded entirely, so even an explicit
  refusal reported success.

**Provenance finding (`e6700a0`).** The method collision predates submission but did not
reach the paper: the mode-split tables use row groups nothing in this repo emits, and the
extractor's own artefact has zero rows of data in every incremental table. Sharper point
for N10: `paper/tables/` and `paper/evaluation.tex` are **untracked**, so the published
tables have no provenance in the repository at all. The revision is the first version in
which the documented pipeline actually produces them.

## Landed — measurements

- `9408c1c` / `ac6a5bf` — order-sensitivity at n=30 **withdraws the 17× claim**. On the
  exclude-2-COV basis (implemented default in `make_tables/filters.py:33`), semantic
  worst-case spread is 0.0818 R / 0.0562 P against description's 0.4615 / 0.5182, and
  semantic recall is unmoved on 18 of 24 folds. Never state it as a ratio. The shipped run
  sits at percentile 0.29–0.45 — not a favourable draw.
- `9408c1c` — NE recall interval: of 42 folds delivering a ¬e⁻, **14 move**, all to recall
  exactly 1.0000. Fourteen complete, one exactly equivalent; the difference is the converse
  condition.
- `ad4cd5b` / `3af7fae` — busybox, measured separately: `n_ne` = 1 on all 9 folds, tier
  max Δ **0.0027** against 0.0909 elsewhere, exact equivalence 0/9. The ordering effect
  **shrinks with model size**, so the "up to 0.09" is driven by the small knowledge bases
  and is invisible at scale. And busybox demonstrates the two-background seam in one pair
  of numbers: NE retained on every fold (not entailed in Reduce's context) while the recall
  interval is +0.0000 on every fold (entailed in the delivered context).
- `2d1c791` — ADR-0015 closed as deliberately not implemented. The published example-mode
  table **does** reproduce (`shuffle_bias = true` at `0b0313a`), so C2's strongest claim is
  withdrawn; implementing it would invalidate 168 QuAcq folds for no change in any number.

## Running

| job | state |
|---|---|
| busybox `rs_1n` NE measurement | 10 h 52 m, fold 0 done at 4.10 h; required so all 12 busybox ConGen folds share one code state |
| item 5 — REAL-FM-4 example-first | `rs_m` f1/f2 remaining; 2cov 4.98 / 1.86 / 2.25 h, rs_m f0 3.01 h |

## Queue, agreed

1. busybox `rs_1n` completes → **code state closes**.
2. Re-score everything through `run_compare`; report `exact_equiv`, attributed to the
   per-example split.
3. **Re-time the 6 REAL-FM-4 example-first units sequentially**, gated on a falsification:
   their deterministic content must be identical to the committed files. Identical →
   replace, one source. Not identical → stop and report, because that finding outranks the
   timings.
4. Probe busybox `2cov` / `ff` at cap 1,000 to fill `EXAMPLE_FIRST_BY_SAMPLING` from
   measurement. Cap stays 1,000.
5. The 12 busybox example-first folds.

Steps 2 and 3 are independent — 2 needs only busybox, 3 needs both jobs stopped.

## Timing provenance (`b615d8a`, `4bc6c0b`)

Contention cannot change a SAT answer, so every quality number is unaffected — |B′|
reproduced 517 / 209 / 502 against committed `n_mss` while other jobs ran. The one path
from CPU load to a deterministic number is the 6 h wall-clock guard; checked across 153
folds, **0 timeouts**, all stopped on deterministic rules.

Timing is affected: busybox fold 0 took 4.10 h against the ledger's 3.94 h alone, **+4%**.
The ledger's `started_utc` / `finished_utc` make the boundary computable: **0 of 238 units
overlap another ledger unit**, and exactly 6 ran alongside a non-ledger job. Rather than
carry two sources, step 3 removes the second one.

Splitting the files into two directories was considered and **does not work**: the loader
keys on `(model, strategy, mode, method)` and the path is not in that key, so the same unit
in two directories collapses to one entry — 2 files in, 1 out, demonstrated. It would
reintroduce `2157122` one level deeper.

## Unresolved

1. The route that produced the published Tables 13/14 is outside the repo and unidentified
   beyond "not `extract_results.py`". Regenerating replaces it rather than reproducing it.
2. `Overleaf/SoSyM/main-r1.tex` and `Overleaf/AAAI/appendix.tex` are now committed in the
   manuscript clone (`0d45be1` … `210bfae`), so the quoted content is verifiable from
   history rather than from a working-tree file. That tree is still not reachable from this
   machine, so the verification has been done on your side, not here — the citation is
   sound, the local check is not available.
3. **Now a gate, not a note.** `tools/sosym_r1/check_timing_provenance.py` refuses to let
   tables be built from contended timings and exits non-zero. It currently reports
   0 ledger x ledger overlaps and 5 units sharing with a non-ledger job — the same set the
   hand analysis found, plus `rs_m` fold 1, which finished after that analysis.

   Note on placement: `reproduce_tables.sh` is **ConMin's** pipeline
   (`apps/conf_conmin/...`, `data/results_conmin`) and never touches the SoSyM ledger, so a
   gate added there would not run before SoSyM tables. It belongs on the SoSyM path, which
   has no single entry script yet — that is a gap worth closing when step 2 runs.

   The half that cannot be automated is recorded as DATA in `NON_LEDGER_JOBS`: the
   intervals of every measurement, scoring and probe job that ran outside the ledger,
   recovered from the launch logs' creation and modification times under the session
   scratch directory. A future job must append its interval or the gate goes blind, and the
   docstring says so. After step 3 the check is expected to report nothing; the file states
   that reporting nothing is the state it exists to protect, so it is not removed as dead.
4. busybox `rs_2n` / `rs_3n` stay out of scope: never completed in the sweep, no baseline.
