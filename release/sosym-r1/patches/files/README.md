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
`PROVENANCE.md` recording a fingerprint of the generator's own bytes.

Running it here leaves the repository unchanged: `git status` stays clean, because every
one of those files is regenerated identical to the committed copy. That is the check —
if a file does change, the tables you are reading are not the ones this code produces.
The fingerprint is a hash of the generator rather than a commit id precisely so that it
survives this round trip; a commit id would name the checkout, not the code.

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
a second. `data/results_sosym/configs/` holds one generated config per cell:

```bash
python3 -m apps.run_cv data/results_sosym/configs/congen_REAL-FM-7_ff.toml -o /tmp/one-cell
```

To score that fold against its target theory, use `run_compare`'s CLI mode, which writes
its evaluation to a separate file:

```bash
python3 -m apps.run_compare --kb /tmp/one-cell/congen/REAL-FM-7_ff_cv_incremental.json \
    --oracle data/fms/REAL-FM-7.uvl --bias data/bias/REAL-FM-7-bias.json \
    -o /tmp/one-cell
```

⚠ Do **not** point `run_compare`'s config mode at the committed trees to score a new
fold: in that mode it writes each evaluation back into the file named by `kb_dir`, so it
would re-score the 28 committed results in place and never touch your new one.

**What matches on a re-run, and what does not.** The learned knowledge base, the
accuracy, the negative examples, the metric values and the summary all reproduce
exactly. The *byte layout* of a scored JSON does not: the scorer's output order depends
on `PYTHONHASHSEED`, so element order within a result — and the timing block, which
measures your machine — will differ between runs. This is expected. Compare values, not
file hashes.

Cost varies enormously across cells — seconds for REAL-FM-7, hours for busybox — so read
the cell name before launching one.

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
