# ea2468 example sets + CV folds (SoSyM revision, C5)

Status: in progress — started 2026-08-21
Branch: `feat/sosym-r1` (from `feat/conmin`)
Scope: **generation only**. No ConGen/QuAcq/ConMin, no `run_cv.py`, no
`run_conmin_eval.py`, no `run_compare.py`, no `extract_results.py`, no
`make_tables`, no `reproduce_tables.sh`.

Goal: six example sets + six CV fold files for `ea2468` (1,408 features), with
wall-clock / peak RSS / |E+| / |E-| / size / sha256 for each. Answers reviewer
R1-Q8 by making ea2468 the endpoint of the scalability curve
(|B| = 2,047,362, up from busybox's 6,635).

## Invariants

- `seed = 82`, `n_folds = 3` — hardcoded in `tools/sosym_r1/gen_ea2468.py`.
- Touch no other knowledge base (REAL-FM-7, fqa, arcade-game, REAL-FM-4,
  busybox). Enforced by the driver's before/after snapshot.
- Nothing for `linux-2.6.33.3` (dropped from the paper 2026-08-21).
- No writes to `data/results/`, `data/results_conmin/`, `Overleaf/`, any `.tex`.
- No edits to `run_conmin_eval.py` or `conacq/eval/conmin_cv_evaluator.py`.
- No source changes.

## Gates

- 6 h per strategy, driver-enforced, everything except 2-COV. On trip: record,
  exit 2, report, stop. No relaxed retry, no partial-coverage variant, no seed change.
- 2-COV unbounded (approved 2026-08-21).

## Order

`ff` → `rs_1n` → `rs_2n` → `rs_3n` → `2cov --no-timeout` → `rs_m --m <2cov count>`
→ `folds` → `report` → `verify_examples_bundle.py .`

`rs_m` last and with `--m`: absent `m`, `generate_examples.py:152-157` derives it
by running a full 2-COV pass, paying for 2-COV twice.

## Environment finding (blocker, resolved) — see reports/

The stated environment was not present: **no `../explanation` beside the repo,
no venv**, so `import explanation` failed and nothing in the generation path
could run. `conacq/examples/data_structures.py:12` and
`conacq/oracle/fm/oracle.py:19-20` depend on it (the SAT checker that classifies
E+ vs E-), so this was not cosmetic.

Resolution: commit `4b47c9b` ("build: consume canonical ../explanation, drop the
in-repo copy") records the deleted in-repo tree as byte-identical to canonical.
Restored `explanation/` from `4b47c9b^` and `profiling/` from `925fcb7^` into a
scratchpad venv (`--system-site-packages` + a `.pth`). **Nothing in the repo or
the system Python was modified.**

Validated empirically rather than assumed: regenerated the deterministic
strategies for four committed models and byte-compared.

| model | features | strategies compared | result |
|---|---|---|---|
| REAL-FM-7 | 14 | rs_1n, rs_2n, rs_3n, rs_m, 2cov | 5/5 byte-identical |
| arcade-game | 65 | rs_1n, rs_2n, rs_3n, rs_m, 2cov | 5/5 byte-identical |
| fqa | 179 | rs_1n, rs_2n, rs_3n, rs_m, 2cov | 5/5 byte-identical |
| REAL-FM-4 | 291 | rs_1n, rs_2n, rs_3n, rs_m, 2cov | 5/5 byte-identical |

20/20. Feature ordering, RNG stream and SAT classification all reproduce.

## Second finding: FF is not reproducible under `seed = 82`

`ff` did **not** reproduce, for REAL-FM-7 or arcade-game. Cause is in the repo,
not the environment:

- `conacq/example_generators/base.py:33` — `self.features = oracle.get_variables()`
- `feature_frequency.py:57-60` builds `coverage` by iterating that
- `_get_uncovered_pos` (`:150-158`) walks `coverage.items()` and the result goes
  to `self._rng.shuffle(uncovered)` (`:185`), so a hash-dependent order changes
  which target the seeded shuffle picks.

Evidence: three default runs → three distinct sha256; two runs with
`PYTHONHASHSEED=0` → identical sha256. The five committed `*_ff.json` have the
same property. Left as-is (no source change in scope, and leaving
`PYTHONHASHSEED` unset matches how the committed five were produced).
`ea2468_ff.json` is therefore a valid FF set but not bit-reproducible.

## Commit policy

≈68.6 kB/example ⇒ rs_1n ≈ 96 MB, rs_2n ≈ 193 MB, rs_3n ≈ 290 MB, against
GitHub's hard 100 MB/file and no git-lfs. Those three are already gitignored.

Commit: every set measured ≤ 50 MB, all six fold files,
`tools/sosym_r1/measurements.jsonl`, and both canonical configs updated for
ea2468. Anything else over 50 MB gets gitignored and reported with sha256.
Push the branch. No merge.
