# ConGen — evaluation artifact

Source code, data and result tables for the ConGen paper. This repository contains the
ConGen implementation **as evaluated in the paper**, together with every input the
reported numbers were computed from. Ongoing development happens elsewhere; nothing here
is intended as a maintained library.

## Install

Requires Python ≥ 3.11.

```bash
pip install .
```

The SAT infrastructure (`explanation`) is pinned to a public tag and installed
automatically. No sibling checkout is needed.

## Reproduce the tables

One command, from the committed data:

```bash
./reproduce_tables_sosym.sh
```

It writes `data/results_sosym_r1/tables/` — `results_tables.{md,tex}`,
`corrected-gap-table.md`, `significance.md`, `target-clause-counts.md`, and a
`PROVENANCE.md` recording the generator's git SHA.

Every step is gated and the script stops at the first failure. Two gates run before any
table is written:

- **`apps/sosym_r1/check_timing_provenance.py`** — refuses a runtime measured while
  another sweep unit was in flight.
- **`apps/sosym_r1/check_paper_numbers.py`** — recomputes every number quoted in the
  paper from the committed data. 93 checks.

### Re-running the acquisition itself

The **whole sweep** is not re-runnable from here: it took weeks of machine time and one
busybox fold alone is 15.5 h. The results are committed evidence, not a table input.

A **single cell** is a different matter, and worth trying — REAL-FM-7 completes in under
a second and reproduces byte-for-byte. `data/results_sosym/configs/` holds one generated
config per cell:

```bash
python3 -m apps.run_cv data/results_sosym/configs/congen_REAL-FM-7_ff.toml -o /tmp/one-cell
python3 -m apps.run_compare data/results_sosym_r1/compare_configs/score_congen.toml
```

Cost scales enormously across cells — seconds for REAL-FM-7, hours for busybox — so read
the cell name before launching one. `apps/conf/run_cv_config.toml` drives a batch rather
than a single cell; the per-cell configs above are the ones to start from.

## The two result trees

| role | path | meaning |
|---|---|---|
| OLD | `data/results` | the tree the originally published tables were computed from |
| NEW | `data/results_sosym_r1` | re-scored, each fold against its own oracle |

**Both are required.** The correction reported in the paper rests on comparing them, and
a table that mixes a column from one with a column from the other reproduces from
neither. That is not hypothetical: it is the defect the correction itself documents.

## What is not included

The released example sets cover the cells reported in the paper. Sets for
busybox RS(2n) and RS(3n), and the `ea2468` family, were generated during the
study, never completed a run, and are **not** included — they produced no number
here, and shipping them tripled the size of every clone. `apps/conf/generate_cv_folds_config.toml`
lists the 28 cells that do have results, and no more.

## Provenance

This repository is derived from a private working repository where ConGen is developed
alongside unrelated work. Only what the paper rests on is published here: the
implementation as evaluated, the inputs, the results, and the code that turns them into
the tables. The derivation is scripted, so it can be repeated for a later version rather
than assembled by hand.

**The results were re-scored after a defect was found in the scoring step.** Four of the
five knowledge bases had been compared against the wrong model's target theory, which
inflated some figures and deflated others. Both trees ship — `data/results` as
originally computed, `data/results_sosym_r1` after the correction — because the
disclosure in the paper is a comparison between them, and a reader given only the
corrected numbers could not check it.

## Layout

```
conacq/          the ConGen implementation
apps/            entry points; apps/sosym_r1/ is what the table pipeline runs
tools/sosym_r1/  sweep machinery and one-off measurements — not part of reproduction
data/            feature models, examples, folds, bias, and the two result trees
tests/           the suite
```

## Citing

See `CITATION.cff`.

## License

MIT — see `LICENSE`.
