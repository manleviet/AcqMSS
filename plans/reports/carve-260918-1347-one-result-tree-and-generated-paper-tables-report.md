# CC-A ×2 — drop the OLD tree, and generate every paper table

Both prompts, one carve, plus two rounds of follow-up. Source `bb46bc9`
(feat/sosym-r1) → artifact `1eaed23`. Tag not applied; commands for it at the end.

**Revised 2026-09-18 after the follow-up.** The cost table had a defect — a negative
duration — and the numbers below are the post-fix ones. See "Follow-up".

## Acceptance (fresh clone, fresh venv, no sibling checkout)

| criterion | result |
|---|---|
| `pip install .` | ok — `explanation` resolves from the public tag `v0.1.0`; no sibling checkout needed |
| `./reproduce_tables_sosym.sh` | exit 0 |
| prose-number gate | **99** checks, all reproduce |
| table gate | **1,420** cells checked, 0 mismatched; 4 property checks green |
| suite | **324 passed, 17 skipped, 0 failed** (Python 3.11.14, uv venv, `.[dev]` only) |
| round-trip | `git status --short | wc -l` = **0** |
| OLD-tree grep | 41 hits, every one read; none refers to a second tree |
| keep-list | 155 patterns → 630 selected → **618 files** shipped |

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
| `tab:AcqMssruntime` | 3 phases + total, in checks and ms | per-fold mean | `profiler.paper_consistency_checks`, `performance.redundancy_consistency_checks`, `profiler.shared_preprocessing_*`, `congen_runtime_ms`, `reduce_runtime_ms`, `runtime_ms` |
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
tab_AcqMssruntime            300          tab_runtime_comparison       133
tab_accuracy_all              42          tab_rule_learners            227
tab_comparison_strategies    114          tab_significance              36
tab_semantic_pr              114
tab_kb_size                   81          12 fragments
                                          gate re-derives 1,420 data cells
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

**Now asserted, after the follow-up** (see below): runtime spread and the five
order-sensitivity figures.

**Still unassertable:** contention 5.3 % (B6 ⟨CT⟩). It comes from re-running units that
had shared the machine; `sweep-ledger.json` carries `started_utc`/`finished_utc` per unit
but does not label the re-timed pairs, so the comparison cannot be reconstructed. Label
those pairs and it becomes assertable. The paper drops it.

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
10. **A3's shape — superseded by the follow-up.** One fragment, rows (KB, sampling),
    eight quantity columns. `acqmss_runtime` is **not** used as a duration: it accumulates
    over 3,000+ nested recursive calls (149.9 s against a 15.2 s run), which is the unit
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


---

# Follow-up (2026-09-18)

## 1. The defect: a printed negative duration — confirmed and fixed

`tab_AcqMssruntime_phases.tex` printed `runtime (ms), AcqMss = -1{,}723` for KB₂.

**Root cause, measured.** The derivation was
`congen_runtime_ms − reduce_runtime_ms − preprocessing`. Over all 84 folds:

| relationship | violations |
|---|---|
| `reduce_runtime_ms` is inside `congen_runtime_ms` | 0 of 84 |
| `shared_preprocessing_runtime` is **disjoint** from `congen_runtime_ms` | 0 of 84 |
| `congen_runtime_ms` + preprocessing ≤ `runtime_ms` | 0 of 84 |
| `profiler.congen_total_time` == `performance.runtime_ms` | 0 of 84 |

Preprocessing was being subtracted from a quantity that never contained it. On fqa RS(n)
the mean loop is 3,865 ms and preprocessing 5,536 ms, so the result went negative. The
cell gate agreed because it re-implemented the same subtraction — a re-derivation shares
the definition and will agree with a wrong one.

**Fix.** AcqMss ms = `congen_runtime_ms − reduce_runtime_ms`. The three phases sum to
less than the total; the remainder (5.8 ms to 11.7 s per fold) is setup and teardown
outside every timing scope and stays unattributed rather than being folded into a phase
that did not spend it.

## 2. Property checks that do not depend on the derivation

`apps/sosym_r1/audit_tables/properties.py`, run by the gate:

| # | property | source |
|---|---|---|
| P1 | no printed duration is negative | the fragment |
| P2 | phase durations sum within their total; slack reported | the fragment |
| P3 | declared parts sum to the declared total (checks) | the fragment |
| P4 | the profiler's scopes contain what is subtracted from them | the JSON, all 84 folds |

**All four observed failing before they counted.** P1 fires on **8 units** of the
pre-fix fragment (KB₁ 2-COV, KB₂ RS(n)/RS(2n)/RS(3n)/2-COV, KB₃ 2-COV, KB₄ 2-COV,
KB₅ 2-COV). P2, P3 and P4 were each fired on deliberately broken input — an inflated
phase, a reduced part, and a copy of the tree with `reduce_runtime_ms` set past its
loop. The per-fragment cell mutation was re-run: red on **12 of 12**.

Gate output now reports `cost-table properties: 30 units checked …; largest unattributed
runtime slack 11748 ms` beside the cell count.

## 3. Every derived column, with its expression

Everything not listed is a direct field read per fold and averaged over the three folds.

| fragment | column | expression |
|---|---|---|
| `tab_AcqMssruntime` | AcqMss ms | `performance.congen_runtime_ms − performance.reduce_runtime_ms` |
| `tab_AcqMssruntime` | GenNE/QX ms | `profiler.shared_preprocessing_runtime.total × 1000` (s → ms) |
| `tab_AcqMssruntime` | total checks | AcqMss + Reduce + GenNE/QX checks |
| `tab_accuracy_all` | ± | sample standard deviation (n−1) over the three folds |
| `tab_semantic_pr` | eq. | `attained/scored`, counted over folds where `exact_equiv` is not null |
| `tab_iterative_semantic` | stop | set of `convergence_reason` over folds, abbreviated |
| `tab_iterative_*` | bold | argmax of the three methods' F1 per (KB, sampling) |
| `tab_rule_learners` | all four | mean over **scored** folds only; degenerate folds marked, never averaged as 0 |
| `tab_significance` | wins | `wins/n`; `p` as `$< 10^{-7}$` below that floor; claim 2 as not testable |

`tab_AcqMssruntime.tex` carries this in a `%` header beside the numbers, including the
measured scope containment, so the derivation travels with the table rather than living
only here.

## 4. Prose numbers, resolved

**Runtime spread — asserted under a named definition.** Largest per-cell max/min of fold
`runtime_ms`: **1.5249×** (REAL-FM-4 2-COV), over 28 cells. The drafts' 2.8× is not this
quantity.

**2.8× is reproducible after all, and the drafts mislabel it.** It is the
**description : semantic spread ratio** from the order-sensitivity probe — per fold, the
larger of the P and R ranges for the description tier divided by the same for the
semantic tier. Median **2.7857×** over 67 folds with a finite ratio. B6 calls it "the
spread between folds of the same cell, which reaches a factor of ⟨RS⟩", which is a
different quantity (1.52×). **The sentence and the number do not describe the same
thing; one of them has to change.**

**Order sensitivity — committed and asserted.**
`data/results_sosym_r1/order_sensitivity/order_sensitivity.json`, with provenance:
commit, command, population, determinism and method. No global seed — permutation `p` of
fold `i` uses `Random(1000·i + p)` and the example shuffle uses that fold's committed
`shuffle_seeds`, so re-running reproduces it exactly.

| draft figure | committed measurement |
|---|---|
| 20 orders | **20** ✓ |
| 24 folds | **84** — the whole tree |
| 18/24 moved | **77/84** moved |
| ⟨SS⟩ 0.0818 | largest semantic spread **0.8385** |
| ⟨DS⟩ 0.4615 | largest description spread **0.5182** (0.4615 is the largest description *recall* range, so the draft quoted one metric of the tier) |

⚠ **The 24-fold population is not reconstructible.** Which 8 cells it covered is recorded
nowhere in the drafts, the hub, or the repository, so the four figures that moved cannot
be checked against it. The committed run is over all 28 units, which needs no record of a
selection. Per the instruction, the measured values are reported and asserted, never the
drafts'.

**0.0919 closed** — not quoted in the paper.

## 5. Tag: re-pointing v1.0.0

Remote state, read not assumed:

```
52741509…  refs/tags/v1.0.0        (annotated tag object)
54b8d1cf…  refs/tags/v1.0.0^{}     (the commit it names)
54b8d1cf…  refs/heads/main
```

Nothing has reached the reviewers, so v1.0.0 **moves** rather than being superseded.
`main` moves with it: a tag pointing at a commit on no branch is not fetchable by the
usual clone.

**Anyone who fetched v1.0.0 before the move keeps the old object.** Git does not recall a
tag; a client that already has `5274150` keeps it until it is told to prune. Today that
set is empty — the tag was pushed but no Zenodo record, no GitHub Release and no
reviewer link exists, which is what makes moving it safe rather than merely convenient.

Run these from Terminal, **on the day you tag**:

```bash
# 0. date-released must equal the tag date, or release hygiene refuses the carve
cd ~/Development/GitHub/AcqMSS
$EDITOR release/sosym-r1/patches/files/CITATION.cff     # date-released: <today>
git commit -am "release(sosym-r1): date-released is the tag date"

# 1. carve fresh from the committed state
./release/carve.sh sosym-r1 /tmp/congen-artifact

# 2. replace main — the artifact is one unrelated root commit, so this is a force push
cd /tmp/congen-artifact
git remote add origin https://github.com/manleviet/ConGenEvaluation.git
git push --force origin main

# 3. move the tag
git push origin :refs/tags/v1.0.0
git tag -a v1.0.0 -m "ConGen evaluation artifact for the SoSyM revision"
git push origin v1.0.0

# 4. verify — three lines, nothing else
git ls-remote https://github.com/manleviet/ConGenEvaluation.git
```

Step 4 must print exactly three refs: `refs/heads/main` and `refs/tags/v1.0.0^{}` both at
the **new** commit SHA (the one `carve.sh` printed at step 1), and `refs/tags/v1.0.0` at
a new annotated-tag object. If `main` and `v1.0.0^{}` disagree, stop — the tag is naming
something other than what is published.

## Unresolved, after the follow-up

1. **B6's runtime-spread sentence** describes a fold-to-fold runtime spread but quotes
   2.8×, which is the description:semantic spread ratio. Either the sentence changes to
   describe the ratio, or the number changes to **1.52×**.
2. **⟨SS⟩ and ⟨DS⟩ in A5** need replacing with 0.8385 and 0.5182, or with a stated
   per-metric definition if 0.4615 (description recall) is the intended quantity.
3. **Contention 5.3 %** stays unasserted until the re-timed pairs are labelled in
   `sweep-ledger.json`.
4. Items 2–3 of the original unresolved list stand: the manuscript's tables must be
   re-typed from the fragments, and the `tab:runtime_comparison` /
   `tab:AcqMssruntime` captions must state the aggregation.


---

# Follow-up 2 (2026-09-18) — the missing profiler counters

## The report was right about the reads, and wrong about the number

Five fold-0 records carry no `shared_preprocessing_runtime` /
`shared_preprocessing_quickxplain_checks`, and both the generator and the gate read the
absence as `0` through `.get(key, 0)`. That route is indefensible and is now gone.

**But the resulting number was correct, and changing it would introduce an error.**

## Why those five folds lack the keys

Measured over all 84 congen folds, then proved from the code:

| | |
|---|---|
| folds lacking the counters | **5** — all fold 0: KB₁ RS(n), KB₁ RS(m), KB₂ RS(m), KB₃ RS(m), KB₄ RS(m) |
| folds with `train_size.negative == 0` | **5** — the same five |
| correspondence | **exact, both directions** |
| what else those folds lack | the whole QuickXplain family: `quickxplain_calls`, `quickxplain_runtime`, `qx_calls`, `qx_runtime`, and the two shared counters — 15 profiler keys instead of 21 |

`generate_ne.py:86` is `if not testsuite.testcases: return []`, and the counters are
created lazily inside the per-testcase loop below it (`:162`, `:166`). GenerateNE
explains **negative** examples. A training split with none never enters the loop, so the
counters are never created.

**Not a resumed partial, not a pre-instrumentation run.** The phase ran zero times and
cost zero checks and zero milliseconds. That is a measurement, not a gap.

## Therefore the fold belongs in the mean, at zero

KB₁ RS(m) GenNE/QX checks = mean(0, 9, 9) = **6**, which is what the fragment prints.
Averaging over the two folds that recorded a counter would give 9 and **overstate the
preprocessing cost by half**, by dropping a fold in which the phase genuinely cost
nothing. The invariant "a quantity absent from a fold is absent, never zero" is right in
general and does not apply here, because the quantity is not absent — it is zero, and
the fold says so through `train_size.negative`.

**No number in the fragment moved.** Verified: the regenerated table is byte-identical
to the committed one apart from the header comment.

## What did change: the route

The zero is now justified **from the fold**, never from the absence. Both readers ask
`train_size.negative == 0`; if a counter is missing while negatives are present, they
raise rather than default — a different fault, and one that would otherwise understate
the cost silently.

### Every default-on-missing read, enumerated and decided

Measured first: across 84 congen folds, which keys are ever actually absent?

| key | absent in | decision |
|---|---|---|
| `shared_preprocessing_runtime` | 5 folds | **justified zero**, from `train_size.negative == 0`; raise otherwise |
| `shared_preprocessing_quickxplain_checks` | 5 folds | same |
| `n_queries`, `convergence_reason` | 84 folds | absent by design — ConGen is passive; already rendered `--` |
| `runtime_ms`, `congen_runtime_ms`, `reduce_runtime_ms`, `consistency_checks`, `redundancy_consistency_checks` | **0 folds** | **strict** — raise on absence |
| `paper_consistency_checks`, `congen_total_time` | **0 folds** | **strict** — raise on absence |
| `n_mss`, `n_kb`, `n_bias`, `n_ne`, `accuracy` | **0 folds** | **strict** |

Every `.get(key, 0)` and `or 0` in `read_results.py` is gone; `perf_mean`,
`profiler_scalar` and `profiler_total_ms` in the gate's `reread.py` raise `Absent`. A
default on a key that is never absent can only ever hide a future fault, which is
exactly what it did here.

## P5 — fold counts, declared and enforced

`properties.fold_counts(congen_dir, declared=3)`: every unit has the declared number of
folds, and no fold silently drops out of a mean. The fragment header states the
declaration, so the two cannot drift apart.

**P5 does not fire on the committed tree, and that is the correct outcome rather than a
weak test** — every unit has three folds and every fold contributes to every mean. Its
failure path was therefore exercised on constructed input, as P2–P4 were:

| constructed fault | result |
|---|---|
| counter missing while the split has 4 negatives | **red** — P5 names the fold and the count |
| the same, through the generator | **red** — `Missing`, not a default |
| the same, through the gate | **red** — `Absent`, not a default |
| a unit with 2 folds where 3 are declared | **red** |
| `performance.reduce_runtime_ms` deleted | **red** — `Absent` |

5 of 5. The per-fragment cell mutation (12/12) and P1–P4 (4/4) were re-run and still hold.

## Acceptance, re-run

`pip install .` ok · script exit 0 · **99** prose checks · **1,420** cells / 0 mismatched
· properties green over 30 units · **324 passed / 17 skipped / 0 failed** · round-trip
**0** · grep 41 hits, none naming a second tree · 618 files. Source suite **680 passed,
1 skipped** — the documented baseline.

## Unresolved, unchanged

The four items from Follow-up 1 stand. Nothing here adds one: the five folds are
explained, and the explanation is in the fragment header rather than only in this report.
