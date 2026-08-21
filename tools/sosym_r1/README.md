# tools/sosym_r1 — ea2468 example sets + CV folds

One-off tooling for the SoSyM revision, checklist item **C5**: generate the six
example sets and six CV fold files for `ea2468` (1,408 features), and measure
what each costs. Branch `feat/sosym-r1`, cut from `feat/conmin`.

This is **generation only**. No evaluation runs — not `run_cv.py`, not
`run_conmin_eval.py`, not `run_compare.py`, not `extract_results.py`, not
`make_tables`, not `reproduce_tables.sh`. Whether ea2468 can be evaluated at
|B| = 2,047,362 is a separate and far more expensive question, decided later.

## The two traps this tooling exists to prevent

**Other knowledge bases get overwritten.** `apps/conf/generate_examples_config.toml`
lists five active `[[models]]`, and `generate_examples.py` has no skip-if-exists —
`ExampleIO.save_json` overwrites unconditionally. A plain run destroys 30
committed example files whose numbers the paper depends on. `gen_ea2468.py`
builds a throwaway config containing only ea2468 and one strategy, and asserts
before and after each run that no other model's file moved. The same applies to
the fold config, which overwrites every fold file whose example set it finds.

**`rs_m` is not independent.** With `m` absent from the model block,
`generate_examples.py:152-157` computes it by running a **full 2-COV pass**, so
running `rs_m` before `2cov` pays for 2-COV twice. The relation is
`m = |E⁺| + |E⁻|` of the 2-COV set — exact on all five committed models
(9/9, 14/14, 16/16, 18/18, 21/21). `gen_ea2468.py examples rs_m` refuses to run
without `--m`.

## Order

```bash
python3 tools/sosym_r1/gen_ea2468.py examples ff
python3 tools/sosym_r1/gen_ea2468.py examples rs_1n
python3 tools/sosym_r1/gen_ea2468.py examples rs_2n
python3 tools/sosym_r1/gen_ea2468.py examples rs_3n
python3 tools/sosym_r1/gen_ea2468.py examples 2cov --no-timeout   # overnight
python3 tools/sosym_r1/gen_ea2468.py examples rs_m --m <count printed by 2cov>
python3 tools/sosym_r1/gen_ea2468.py folds
python3 tools/sosym_r1/gen_ea2468.py report
python3 tools/sosym_r1/verify_examples_bundle.py .
```

Each `examples` run appends wall-clock, peak RSS, `|E⁺|`, `|E⁻|`, byte size and
sha256 to `measurements.jsonl`, so the cost table is a byproduct of the run
rather than something reconstructed afterwards. `report` renders it.

## Gates

- **6 hours per strategy**, enforced by the driver, for everything except 2-COV.
  If one trips, the driver records where it got to and exits 2. Do not retry with
  a relaxed criterion, do not invent a partial-coverage variant, do not change the
  seed. A malformed example set is worse than a missing one.
- **2-COV runs unbounded** (approved 2026-08-21) — pass `--no-timeout`. It is the
  expensive one: `allpairspy` is pure Python and superlinear, and at 1,408 boolean
  parameters it covers C(1408,2) ≈ 990,000 feature pairs. Measured on the same
  library at k = 100/150/200/300/400: 0.9/3.4/9.4/33/114 s, extrapolating to
  roughly 2.5–7 h here, peak RSS ~2–4 GB.

## Invariants

- `seed = 82`, `n_folds = 3`. Pinned project-wide; the driver hardcodes both.
- Touch no other knowledge base. Enforced, not merely requested.
- Generate nothing for `linux-2.6.33.3` — dropped from the paper 2026-08-21.
- Do not touch `data/results/`, `data/results_conmin/`, `Overleaf/`, or any `.tex`.
- Do not modify `run_conmin_eval.py` or `conacq/eval/conmin_cv_evaluator.py`;
  they belong to the ConMin paper.
- No source changes are needed: `generate_examples.py` reads only the UVL through
  `FMOracle`, `generate_cv_folds.py` reads only the examples JSON. Neither needs
  the bias — which matters, because `data/bias/ea2468-bias.json` and `.cnf` are
  **gitignored** (`.gitignore:210-211`) and are not in the repo.

## What gets committed

The example sets are large: ea2468 costs ≈68.6 kB per example, so `rs_1n` ≈ 96 MB,
`rs_2n` ≈ 193 MB, `rs_3n` ≈ 290 MB, against GitHub's hard 100 MB per-file push
limit, with no git-lfs in this repo. Decision (2026-08-21): **gitignore them and
move them out of band**, matching the precedent already set for the bias; Zenodo
at publication.

Commit: `ea2468_2cov.json`, `ea2468_rs_m.json`, `ea2468_ff.json` and any other set
measured at ≤ 50 MB; all six `data/folds/ea2468_*_folds.json`; the two canonical
configs updated with the ea2468 block; `.gitignore`; `measurements.jsonl`.

Do not commit anything over 50 MB. `report` lists those files with their sizes
and sha256 so they can be transferred separately and checked on arrival.

## C11 — regenerating the FF sets

Separate task, same tooling. `feature_frequency.py:59` built its `coverage` dict
by iterating `self.features`, which is a **`set` of strings**, so the target that
`_rng.shuffle(uncovered)` picked depended on Python's per-process string hashing.
`random.Random(82).shuffle` is a fixed permutation *of positions, not of
contents* — the seed fixes the permutation, the hash fixes what it permutes. So
the committed `*_ff.json` are not re-derivable from seed 82. Line 62 sorts the
same set three lines later, and every other generator sorts, which is why only FF
is affected.

```bash
python3 tools/sosym_r1/gen_ea2468.py regen-ff
```

Refuses to run until the fix is in place, so a second irreproducible batch cannot
be produced by accident. It regenerates the FF example sets and their fold files
for all six knowledge bases in one config, and asserts that **only** `*_ff.json`
and `*_ff_folds.json` changed.

Order matters: run this **after** the ea2468 chain finishes, never concurrently —
the two write into the same directories and each one's guard would (correctly)
abort the other. `ea2468_ff` is simply regenerated along with the rest; the copy
from the first pass is superseded, not in conflict.

Two things the command cannot do for you:

- **Re-baseline the goldens.** Six test files read `REAL-FM-7_ff.json`, and
  `tests/test_t11_e2e_learned_kb.py:42` asserts `layer3_golden["congen_ff"]`.
  Changing the input turns it red; that is the tripwire working.
- **Close the test gap**, which is the part worth the most.
  `tests/test_generator_characterization.py` parametrises `_make_ff` and claims to
  lock *"the same generator, run twice with the same seed, yields byte-identical
  examples"*. Both of its reproducibility tests run **inside one process**, where
  `PYTHONHASHSEED` is constant, so FF passed throughout. The test is blind to
  exactly the defect it advertises protection against. Add a case that runs a
  generator in a **subprocess** under varied `PYTHONHASHSEED` and compares
  fingerprints.

⚠ The pre-regeneration data is tagged **`conmin-aaai-data`** (`fd84762`). ConMin's
published numbers do not change and its camera-ready supplement ships the FF sets
from that tag, not from the working tree. Recover them with
`git show conmin-aaai-data:data/examples/<kb>_ff.json`. Do not delete the tag.

## Verification

`verify_examples_bundle.py` imports nothing from this repo — stdlib only — so it
cannot inherit a defect from the code it checks. It re-derives the folds from an
independent reimplementation of `generate_folds` and byte-compares, re-checks
2-COV coverage over every feature pair from the raw rows rather than trusting the
generator, and checks partition and train/test leakage. It passes clean on all
five committed knowledge bases.
