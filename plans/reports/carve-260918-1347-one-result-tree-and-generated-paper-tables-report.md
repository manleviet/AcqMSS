# CC-A ×2 — drop the OLD tree, and generate every paper table

Both prompts, one carve. Source `c77732a` (feat/sosym-r1) → artifact `50d97fb`.
Tag not applied; that is Viet-Man's step.

## Acceptance (fresh clone, fresh venv, no sibling checkout)

| criterion | result |
|---|---|
| `pip install .` | ok — `explanation` resolves from the public tag `v0.1.0`; no sibling checkout needed |
| `./reproduce_tables_sosym.sh` | exit 0 |
| prose-number gate | **89** checks, all reproduce |
| table gate | **1,250** cells checked, 0 mismatched |
| suite | **324 passed, 17 skipped, 0 failed** (Python 3.11.14, uv venv, `.[dev]` only) |
| round-trip | `git status --short | wc -l` = **0** |
| OLD-tree grep | 41 hits, every one read; none refers to a second tree |
| keep-list | 155 patterns → 629 selected → **617 files** shipped |

Environment for the suite count: a venv built by `uv venv --python 3.11` inside the
carve, `uv pip install '.[dev]'`. **The baselines extras are absent there, and that is
what produces 17 skips** — install `baselines` / `baselines-cn2` and those tests run
instead of skipping, which is how an earlier run of mine read 339 passed / 0 skipped.
Record the extras, not just the count.

Previous artifact was 325 passed / 18 skipped. The two that went are named under
"What was removed".

---

# Part A — one result tree

## What was enumerated

Measured against a carve of the pre-change tree (905 files), not against the prompt's
list. Two greps: the one the prompt specifies, and a wider `data/results` scan, because
the specified pattern `results/\b` does not match `output_dir = "data/results"` — `/`
followed by `"` is not a word boundary. The wider scan found 34 files / 100 hits where
the narrow one found 27 / 196.

Sites the prompt named, all confirmed: `check_paper_numbers.py` (OLD, OLD_INT,
`TREES['old']`, section 3, the mode-collapse checks), `measure_corrected_gap_table.py`,
`reproduce_tables_sosym.sh` (:97 gate, :101, :175, :200, :237), `README.md` §Provenance
and the tree table, `docs/*.md`, the keep-list.

**Five sites the prompt did not name**, each found by measurement:

1. **`data/kb_eval/`** — the scored output of an earlier run over `data/results`, three
   files naming `data/results/*_intersected_kb.json`. The keep-list justified it as
   "Three KB evaluation inputs, all still read". Measured: `git grep data/kb_eval` over
   the carve returns **no reader**. The comment was false.
2. **`data/results/old_results/`** — **247 files**, a tree older than the old tree,
   nested inside it. The artifact was shipping two superseded result sets, not one.
3. **`tests/test_evaluation.py`** — two integration tests loading a single learned KB
   from `data/results/old_results/…_fold1_kb.json`. Invisible to every grep because the
   path is assembled from `DATA_DIR`. They went **red**, not skipped, once the tree was
   gone.
4. **`tools/sosym_r1/congen_check_unit_factors.py`** — reads `data/results/congen` and
   nothing else; its own header calls those inputs stale.
5. **`tests/resources/t9_extraction_golden/`** — a golden frozen from the old tree, and
   the four `test_t9_metrics_safety_net.py` tests that read it.

### A defect found while counting

`check_paper_numbers.py` contained 95 `check()` calls but executed 93. Two —
`old interactive: same` and `old interactive: fold count` — sat behind
`folds_of('**/*.json', OLD_INT)`, and `glob.glob` without `recursive=True` matches
nothing for `**/*.json` when the JSONs sit directly in the directory. Measured: 0 files
matched, 36 present. Both were guarded by `if old_int:`, so they skipped in silence in
every carve ever made. They are gone with section 3, but the shape is the one the file's
own docstring warns about.

## What was removed

| removed | why |
|---|---|
| `data/results/` (302 files, incl. `old_results/` 247) | the paper reports one tree |
| `data/kb_eval/` (3) | scored output of that tree; no reader |
| `apps/sosym_r1/measure_corrected_gap_table.py` | two trees by construction |
| `tools/sosym_r1/congen_check_unit_factors.py` | reads `data/results/congen` only |
| `tests/resources/t9_extraction_golden/` (2) | golden frozen from the old tree |
| `data/results_sosym_r1/tables/corrected-gap-table.md` | no longer generated |
| 7 checks in `check_paper_numbers.py` | evidence for the two-tree disclosure |
| 2 tests in `test_t9_metrics_safety_net.py` | read a path the carve no longer ships |

**Check count: 93 → 89.** Removed: the three section-3 defect-signature checks, the two
tree-path assertions, `of those, published in OLD (correctable)`, and one of the two
mode-collapse checks (OLD and NEW merged into one). Re-pointed rather than dropped, with
their new measurements: the aggregation-convention trio now reads the shipped tree
(`0.659711` per-fold mean = summary mean, intersected KB `0.654709`, still a different
number), and the oracle-benefit pair is now computed over all 28 cells rather than the
18 the old tree defined (**smallest benefit 0.0035**, not 0.0919 — see Decisions).
One check was **added**: `cells where ConGen is below the accept-everything baseline`
= 20 of 28, an A5 number that had no assertion. `MINIMUM_CHECKS` 90 → 85.

The two t9 tests removed were `test_extraction_tables_are_byte_identical` (the one
skipped test, which compared stale against stale) and
`test_extract_handles_mixed_old_and_new_schema` (needs a legacy 29-group file to build
its "old" shape from; the shipped tree is 13-group throughout). The other four t9 tests
were re-pointed at `data/results_sosym_r1/congen` and **got stronger**: the schema pin
now asserts over every file rather than the first, and measured 0 of 28 deviating.

---

# Part B — every paper table, generated and gated

## The enumeration

Every `\begin{tabular}` in `Overleaf/SoSyM/main-r1.tex` from `\section{Analysis and
Evaluation}` (l. 546) onward — nine, matching the prompt's list, plus the three it marks
NEW.

| label | quantity per cell | aggregation | source |
|---|---|---|---|
| `tab:fm_summary` | #features, \|B\|, #clauses, domain | static | `data/bias/*-bias-stats.txt`; domain declared in `frozen.py` |
| `tab:example_sizes` | \|E⁺\|, \|E⁻\| | counted | `data/examples/*.json` `positive`/`negative` |
| `tab:AcqMssruntime` | checks / runtime (ms) | per-fold mean | `performance.consistency_checks`, `.runtime_ms` |
| `tab:AcqMssruntime_phases` **NEW** | checks and ms per phase + total | per-fold mean, then mean over samplings | `profiler.paper_consistency_checks`, `redundancy_consistency_checks`, `shared_preprocessing_*`, `congen_runtime_ms` |
| `tab:accuracy_all` | accuracy mean ± sd | per-fold | `folds[].accuracy` |
| `tab:comparison_strategies` | F1 desc/clause/sem | per-fold mean | `evaluation.<tier>.metrics.f1_score` |
| `tab:semantic_pr` **NEW** | semantic P, R, exact equivalence | per-fold mean; eq. as attained/scored | `evaluation.semantic.metrics`, `evaluation.exact_equiv` |
| `tab:kb_size` | \|MSS\|, \|KB\| | per-fold mean | `statistics.n_mss`, `.n_kb` |
| `tab:iterative_accuracy` | accuracy, three methods | per-fold mean | congen + `interactive/*_example_{only,first}.json` |
| `tab:iterative_semantic` | semantic F1 + queries + stop rule | per-fold mean | as above + `n_queries`, `convergence_reason` |
| `tab:runtime_comparison` | total runtime (ms), three methods | per-fold mean | `performance.runtime_ms` |
| `tab:rule_learners` **NEW** | accuracy, semantic P/R/F1 | mean over scored folds | `data/results_sosym_r1/baselines/baselines.json` |
| `tab:significance` **NEW** | claim, n, median Δ, wins, p, Holm | — | `significance_tests.compute()` |

## The fragments

`data/results_sosym_r1/tables/paper/`, one `.tex` per label, each exactly one
`tabular`. Caption, `\label` and `table*` stay in the manuscript.

```
tab_fm_summary                30 cells    tab_iterative_accuracy       133
tab_example_sizes             81          tab_iterative_semantic       330
tab_AcqMssruntime             42          tab_runtime_comparison       133
tab_AcqMssruntime_phases      54          tab_rule_learners            227
tab_accuracy_all              42          tab_significance              36
tab_comparison_strategies    114
tab_semantic_pr              114          13 fragments, 1,417 cells incl. labels
tab_kb_size                   81          gate re-derives 1,250 data cells
```

Rows are the six samplings in the paper's order; columns `$KB_1$`–`$KB_5$` in the frozen
mapping. Two generated markers: `n/a` (unit not run — busybox RS(2n)/RS(3n)) and `--`
(ran, quantity undefined — ConGen's query and stop columns). Neither is ever a zero.
Bold is argmax over the compared methods, computed.

## The gate

`apps/sosym_r1/check_paper_tables.py` + `apps/sosym_r1/audit_tables/`. It imports
nothing from `paper_tables/`: it re-reads the same JSON, re-implements the three
formatting rules, and declares the KB/sampling vocabulary itself, so importing the
generator's list cannot make it agree with a renumbering. Comparison is exact on the
rendered string. **1,250 cells checked, 0 mismatched.**

**Shown failing before it counted.** One numeric body cell was altered in each fragment
in turn; the gate went red on **13 of 13**. Separately: a truncated fragment and a
missing fragment each report `UNPARSEABLE` and exit 1, so an unreadable table is red
rather than skipped.

## The rule-learner run

No paper-grade run existed. Re-run on the corrected five-KB folds with the corrected
scorer; committed at `data/results_sosym_r1/baselines/baselines.json` with provenance.

- 28 units (every unit with an acquisition result; busybox RS(2n)/RS(3n) excluded —
  a baseline cell beside an absent ConGen cell compares against nothing)
- 252 cells = 28 × 3 folds × 3 learners; **72 scored, 180 `too_few_instances`, 0
  `no_rules_learned`**
- reporting rule (declared before any number existed): a cell is scored only when both
  classes have ≥ 10 training instances
- environment recorded in the file: Python 3.11.14, scikit-learn 1.9.0,
  wittgenstein 0.3.5, Orange3 3.40.0
- tiers: accuracy + semantic only; description omitted by design
- **the semantic caveat is carried in the file**: lead with recall. Precision is not
  comparable across the two sides — ConGen counts CNF clauses per learned constraint, a
  rule set counts one clause per rule, and F1 inherits it.

`baselines` / `baselines-cn2` both installed cleanly here, so a reader can reproduce the
CN2 column; Orange3 pulls 87 packages, which is why the extras stay split.

## Prose numbers

Added: **20 of 28 cells below the accept-everything baseline** (A5 ⟨K⟩/⟨M⟩), which
reproduced exactly. Already asserted and re-verified: 74.62 %, 18/28, 1/84, \|Cτ\| 22
and 130, fold agreement 29–80 %, 13/15 2-COV.

**Unassertable, reported rather than asserted:**

- **runtime spread 2.8× (A5 ⟨RS⟩, B6).** Under the drafts' own definition — spread
  between folds of the same cell — the committed data gives **max 1.52×** over
  `results_sosym_r1/congen` (median 1.11×) and **max 1.51×** over `results_sosym/congen`.
  The interactive tree has a 788× outlier and a 1.49× median. No committed tree yields
  2.8× under that definition.
- **contention 5.3 % (B6 ⟨CT⟩).** Derived from re-running units that had shared the
  machine. `sweep-ledger.json` carries `started_utc`/`finished_utc` per unit but does not
  label the re-timed pairs, so the comparison cannot be reconstructed. Label those pairs
  and it becomes assertable.
- **order sensitivity 20/24/18/0.0818/0.4615 (A5).** The probe's output is not
  committed, and the quoted figures are over **24 folds** (8 cells) while the shipped
  tree has 84. A re-run over the whole tree would produce a different population, not a
  confirmation. A run over all 28 cells was still in flight at ~50 min when this was
  written; commit its output and the cell selection, then assert.

---

## Decisions the prompts left open

1. **`measure_corrected_gap_table.py` dropped rather than rewritten.** No gap table is
   emitted any more, so its only remaining job was supplying `cell()` to the numbers
   gate. Those ~40 lines are inlined there, which also removed the `sys.path` sibling
   hack and its FATAL branch. `apps/sosym_r1/` in the keep-list became a file list so
   one file could be left out.
2. **Oracle-benefit population changed from 18 cells to 28.** The 18 were "cells
   published in OLD", a subset only the old tree can define. Over all 28 the smallest
   benefit is **0.0035**, not 0.0919. ⚠ If the paper quotes 0.0919, it is quoting a
   population defined by a tree the paper does not mention.
3. **Section 6 re-pointed at the shipped tree.** `0.524859` was the old published
   number; the convention it guards (per-fold mean ≠ intersected KB) is live, so it now
   asserts `0.659711` vs `0.654709` on the same cell.
4. **Rule for the remaining `data/results` strings.** Inputs naming the old tree are
   re-pointed; **output destinations are left alone**. So
   `extract_results_config.toml` (`data/results/congen` → `data/results_sosym_r1/congen`,
   `paper/tables` → `scratch/tables`) and `run_compare_config.toml` (`kb_dir` →
   `scratch/congen`) changed, while `run_evaluation_config.toml` and
   `run_quacq_config.toml` keep `data/results/{evaluation,quacq}` — those name where a
   reader's own run writes, and `tests/test_cv_fold_partials.py` guards that exact
   spelling as a refuse-to-overwrite check. Re-pointing them would rewrite a safety
   guard to satisfy a string match.
5. **`test_evaluation.py` fixture derived, not dropped.** Its two integration tests now
   read `tests/resources/congen_kb_REAL-FM-7_rs_1n_fold0.json`, generated from fold 0 of
   the committed result by `tools/sosym_r1/make_single_kb_fixture.py`. A CV file cannot
   substitute directly: its constraints live in `folds[]`, so the loader returns an
   **empty** KB and the assertions pass on nothing — the ADR-0019 shape. The generator
   refuses to write an empty fixture. This changed the source repo too; `data/results/`
   itself is untouched there.
6. **The ADR line does not ship.** ADR-0019 records the decision for this repository; in
   the artifact that sentence would be the disclosure it exists to prevent, so a patch
   strips it.
7. **`carve.sh` learned two things.** The output-equals-allowlist gate now subtracts
   files a patch deletes, reading the deletions out of the patches rather than a second
   list that could disagree silently. And the example/fold filter no longer looks for
   `data/results`.
8. **One patch per file.** `drop-adr-citation-not-shipped.patch` and the new t9 patch
   both edited `test_t9_metrics_safety_net.py` and the second could not apply over the
   first; they are folded into
   `repoint-t9-pins-and-drop-unshipped-adr-citation.patch`.
9. **`CITATION.cff` `date-released` set to 2026-09-18.** The hygiene gate requires it to
   equal the tag date. **If the tag slips past today, bump it and re-carve** — the gate
   will refuse otherwise.
10. **A3's shape.** The hub settles it: per-phase over AcqMss + Reduce + GenerateNE,
    reported with a total. Both fragments ship — the paper's current two-quantity shape
    and the per-phase one. `acqmss_runtime` is **not** used as a duration on either side:
    it accumulates over 3,000+ nested recursive calls (149.9 s against a 15.2 s run), so
    AcqMss is the acquisition loop minus the two phases timed once each. That is the unit
    mismatch A3 warns inflates AcqMss against Reduce.
11. **`tab:semantic_pr` is one table, not two.** A reader seeing 1.000 recall beside 0/3
    exact equivalence learns something two tables would keep apart.
12. **`tab:runtime_comparison` is the per-fold mean**, not the 3-fold total — every other
    quantity in the set is a per-fold mean, and one column on a different aggregation is
    the mix §7a exists to prevent. **The paper's caption has to change to match.**

## Unresolved

1. **Does the paper quote 0.0919** (smallest oracle benefit over the 18 old-published
   cells)? If so it needs replacing with 0.0035 or a stated population.
2. **The paper's tables must be re-typed from the fragments.** Every table widens from 3
   KBs to 5 and from 4 samplings to 6, and several cells moved — e.g. `tab:accuracy_all`
   KB₁ 2-COV is **1.000**, the manuscript prints 0.556. Nothing here edits `main-r1.tex`.
3. **`tab:runtime_comparison` and `tab:AcqMssruntime` captions** need to state the
   aggregation (per-fold mean) explicitly.
4. **2.8× and 5.3 %** stay in the drafts without a script behind them until the
   contention pairs are labelled in the ledger and the spread's definition is settled.
5. **Order sensitivity** needs its probe output committed before it can be asserted.
6. **`v1.0.0` is not applied.** Tag `50d97fb` after a fresh carve on the day you tag.
