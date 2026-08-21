# C11 — make FF reproducible under `seed = 82` (pre-sweep gate)

Status: NOT STARTED. Runs **only after** the ea2468 chain finishes. Not in parallel.

Origin: the FF nondeterminism found while validating the environment for C5 was
accepted and promoted to hub item C11.

## Step 0 — sync

`git pull` first: needed for the new `tools/sosym_r1/` (which carries the
`regen-ff` command) and for the tag `conmin-aaai-data`.

## Step 1 — the one-line fix

`conacq/example_generators/feature_frequency.py:59` → `for f in sorted(self.features)`.

Exactly one line. **Do not touch line 62** (`features_list = sorted(self.features)`
is already correct).

Why line 59 and not elsewhere: `coverage` is built from that iteration order,
`_get_uncovered_pos` (`:150-158`) walks `coverage.items()`, and the result is fed
to `self._rng.shuffle(uncovered)` (`:185`) — so a hash-dependent order changes
which target the seeded shuffle picks.

## Step 2 — regenerate

`python3 tools/sosym_r1/gen_ea2468.py regen-ff`

Regenerates ff + ff folds for all six KBs from one config, asserting only
`*_ff.json` and `*_ff_folds.json` change. Refuses to run if line 59 is unfixed,
so a second irreproducible batch cannot be created by accident.

## Step 3 — re-baseline the goldens

Six test files read `REAL-FM-7_ff.json`; `tests/test_t11_e2e_learned_kb.py:42`
asserts against `layer3_golden["congen_ff"]`. It **will** go red — that is the
tripwire firing correctly, not a regression.

Run the full suite. **List every red test and the reason before re-baselining
anything.** Known-good baseline: 507 passed + 1 skipped.

## Step 4 — close the test hole (the valuable part)

`tests/test_generator_characterization.py` has `_make_ff` in its parametrize and
a docstring claiming it locks "the same generator, run twice with the same seed,
yields byte-identical examples … required for any downstream end-to-end replay".
Both reproducibility tests run **in one process**, where `PYTHONHASHSEED` is
fixed for the process lifetime — so ff passed. The test was blind to exactly the
defect it advertised as covering, and has been green ever since.

Add a case that runs the generator in a **subprocess under differing
`PYTHONHASHSEED`** and compares fingerprints. Write it falsifiable, in the style
of the isolation tests already in that file: **prove it red on unfixed code
before reporting it green on fixed code.**

## Invariants

- No KB touched except through `regen-ff`.
- Do not delete the tag `conmin-aaai-data`. ConMin keeps its published numbers;
  its camera-ready supplement ships the ff sets from that tag, not the working tree.
- Do not regenerate `rs_*` or `2cov` for any KB — they reproduce and are unrelated.

## Report must contain

1. The one-line diff.
2. New |E+| / |E-| / size / sha256 beside the old values, old taken via
   `git show conmin-aaai-data:data/examples/<kb>_ff.json`. Numbers are *expected*
   to change — that is the point.
3. Red tests before re-baseline, and after.
4. The new test plus evidence it is red on the unfixed code.
5. Verbatim `git status --porcelain`.
