# R1 minimal-change review: gate and fragments follow the paper

- Date: 2026-09-23
- Paper: `Overleaf/SoSyM/main-r1.tex`, mtime 2026-09-23 14:46, 1,180 lines (was 1,273)
- Source of truth: **AcqMSS** `feat/sosym-r1`; artifact branch derived by carve (see *Where this was done*)
- Gate: **275 → 339 checks** here, **270 → 334** in the artifact · fragment checker: **1,305 cells, 0 mismatched** (was 1,420 over 12 fragments)
- Baseline before any change: `pytest tests/ -q` → no red test names

## Claims in the brief that did not hold, stated first

**1. The `eq.` column is not in `tab_comparison_strategies`; it is in `tab_semantic_pr`.**
And neither fragment was KB-major: both were *strategy-rows × KB-column-groups*, 16
columns wide. The paper's new Table 12 is a **merge of the two fragments** (Desc, Clause,
Sem from one; P, R from the other), transposed to KB-major, with `eq.` dropped. So A1 was
a merge-and-transpose, not a column deletion. Done as the paper prints it;
`tab_semantic_pr` no longer exists and the generator now emits **11** fragments.

**2. `tab_AcqMssruntime` was nine numeric columns, not five.** It carried a duration
beside every phase's check count (`AcqMss ms`, `Reduce ms`, `GenNE/QX ms`). The brief's
`\multicolumn{5}{c}{n/a}` implies the paper's five, so the three per-phase durations are
no longer emitted. They are still computed and their scopes are still asserted — see
*What the per-phase durations cost*.

**3. `tab_biasformula` had no fragment to remove.** It was inline LaTeX in the
manuscript, never generated. A4 is a no-op on the generator; what it does change is that
the h_bin/h_grp/k/reduction figures now have no home in the paper at all (§C).

**4. "Label the checks `letter R1-Qx`" collides with release hygiene.**
`scripts/check-release-hygiene.sh` refuses any `R[0-9]+-Q[0-9]+` in the carved tree —
a numbered reviewer item is decodable by a reader. Labels therefore say
**"the response letter"** without an item number. If the item numbers should be carried,
they can only live in the development repository, and the patch that strips them for the
artifact has to be written.

**5. The paper now says "FLAMA 2.6.0"; the artifact pins `2.6.0.dev4`.** Measured:
`pyproject.toml` pins `flamapy-fw/-fm/-sat==2.6.0.dev4` and the environment that produced
every committed number reports `2.6.0.dev4` for all three. No shipped document quotes the
paper's environment sentence, so D has nothing to align — but the sentence is now false of
the artifact, in the round-8 sense. Either the paper says `2.6.0.dev4`, or it says
"FLAMA 2.6" with no patch level. **Not gated, because I cannot edit the paper and a check
written against the current wording would be red on arrival.**

## A. Fragments

| fragment | change | cells |
|---|---|---|
| `tab_AcqMssruntime` | `\multirow{6}{*}{$KB_k$}`, `\midrule` between blocks, five value columns, n/a as `\multicolumn{5}` | 209 |
| `tab_comparison_strategies` | merged with `tab_semantic_pr`, KB-major, `eq.` dropped | 213 |
| `tab_accuracy_all` | column spec `{lccccc}` | 42 |
| `tab_semantic_pr` | **deleted** (absorbed above) | — |

`check_paper_tables.py` follows: a `_kb_major` walker beside the sampling-major `_grid`,
the cost table read with one header row instead of two, and `_cost_rows` now expands
`\multicolumn` so the property checks cannot index past a row that is short only
typographically. **1,300 cells, 0 mismatched.** `check_table_coverage.py` green.

### What the per-phase durations cost

Dropping three columns removed the input to one property check — "phases sum within their
total" could no longer be asked *of the table*. It is still asked, and of a stronger
object: `PR.timing_scopes` checks the same containment on all 84 folds in the JSON, where
the scopes live. What was removed is a restatement, not a check; the property-summary line
now says so.

## B. New prose numbers, paper value against data

Every one held. `revision_minimal_review.py`, 52 checks.

| § | claim | paper | data |
|---|---|---|---|
| 6.2.1 | KB3 AcqMss checks, RS(n) / RS(3n) | 3,090 / 3,290 | 3,090 / 3,290 |
| 6.2.1 | runtime factor RS(n)→RS(3n), KB3 / KB4 | 3.4 / 8.3 | 3.4 / 8.3 |
| 6.2.1 | 2-COV needs the fewest AcqMss checks **on every KB** | — | holds, 5/5 |
| 6.2.1 | 2-COV AcqMss checks per KB | 10, 10, 1,429, 1,612, 14 | identical |
| 6.2.1 | KBs whose 2-COV set has no positive example | KB1, KB2, KB5 | identical |
| 6.2.1 | their Reduce checks | 300 to 6,648 | 300 to 6,648 |
| 6.2.2 | accuracy rises RS(n)<RS(2n)<RS(3n) on the four run | — | holds, 4/4 |
| 6.2.2 | KB2 RS(m) → RS(3n) | 0.367 → 0.966 | identical |
| 6.2.2 | 2-COV most accurate **on every KB** | — | holds, 5/5 |
| 6.2.2 | accuracy span, KB1 / KB5 | 0.194–1.000 / 0.089–1.000 | identical |
| 6.2.2 | widest span / second widest | KB5 / KB1 | KB5 / KB1 |
| 6.2.2 | no held-out negative is ever accepted | FP = 0 | 0 per fold **and** 0 summed; TP 3,573, FN 832, TN 522 |
| 6.2.4 | Desc ≤ Clause ≤ Sem **on every combination** | — | holds, 28/28 |
| 6.2.4 | exact equivalence on one fold | KB1 RS(3n) | 1 fold: `REAL-FM-7 rs_3n` fold 2 |
| 6.2.4 | …and the only fold with semantic F1 = 1.000 | — | the same single fold |
| 6.1.2 | "The background knowledge BG is empty" | — | `task.set_b == []` on all five KBs, `root_axiom` non-empty on all five |
| 6.1.1 | bias exceeds two million candidates | 2,047,362 | already gated, relabelled to §6.1.1 |

Two notes on B:

- **B2 is the same quantity as the existing `KB4_GROWTH['rs_3n']`** — mean `runtime_ms`
  RS(3n) ÷ RS(n). Both checks are kept: one is the paper's §6.2.1 sentence, the other is
  the letter's justification for the two n/a cells. They assert one measurement under two
  claims, and each names its own source.
- **B6's zero is asserted per fold as well as in sum.** A sum of zero is also what a
  +1 and a −1 would give; the per-fold maximum rules that out, and the other three counts
  are asserted beside it so the zero cannot be an empty sum.
- **The exact-equivalence flag is `fold['evaluation']['exact_equiv']`**, not inside the
  semantic tier. Reading it a level deeper returns `None` on every fold and reports "0
  folds equivalent" against a paper that says 1. It did, in the first run of this work.

## A/B addendum: |C_tau| in constraints (items 10 and 11)

**My independent count agrees with yours on all five.** Counted twice, by two readings
of the same UVL that fail differently — a backwards owner scan (each feature asks which
group keyword precedes it at a smaller indent) and the forward pending-map parser
`count_target_clauses.parse` already in the tree. The per-rule breakdown, which is what
a disagreement would have to name:

| model | per child of mandatory/optional | or/alternative groups | cross-tree lines | total | paper |
|---|---:|---:|---:|---:|---:|
| REAL-FM-7 | 9 | 2 | 2 | **13** | 13 |
| fqa | 57 | 36 | 9 | **102** | 102 |
| arcade-game | 27 | 9 | 34 | **70** | 70 |
| REAL-FM-4 | 159 | 39 | 21 | **219** | 219 |
| busybox-1.18.0 | 830 | 8 | 67 | **905** | 905 |

Fragments follow: `tab_fm_summary` gains the column and **drops "clauses of $B$"**,
spec `lrrrl` (A5); `tab_kb_size` gains the header row `($|C_\tau|$=k)`. The dropped
clause count is still recorded in `data/bias/<model>-bias-stats.txt`. **Both re-count from the UVL** rather than one
reading the other, so a drift between Table 7 and Table 11 shows up as two failures
instead of none. Item 11's pair is asserted against measurements on both sides: 177 is
the mean `statistics.n_kb` of KB3 RS(n) (the Table 11 cell) and 70 is counted from
`arcade-game.uvl`, not read back from this file's own constant.

**One hazard is now in the tree and is worth naming.** |C_tau| means two different
things in this project: clauses (22, 342, 130, 428, 994) and constraints (13, 102, 70,
219, 905), two to seven times apart. The clause counts left the paper in this review but
stay gated, because every semantic recall is measured against them. Both sets are
asserted, each labelled with its unit, and each file says which one it holds.

## C. Checks whose cited section no longer carries the number

The paper renumbered (§5 Evaluation → §6, with §5 now Theoretical Analysis). Beyond
renumbering, these numbers left the paper entirely:

| number | was | now |
|---|---|---|
| \|Cτ\| = 22 / 342 / 130 / 428 / 994, in **clauses** | §5.3 sentence | sentence gone. The review put \|Cτ\| in **constraints** into Tables 7 and 11 instead — a different unit of the same symbol. The clause counts stay gated: every semantic recall is measured against them |
| h_bin, h_grp, k, reduction factors | `tab:biasformula` | table removed; letter quotes them |
| "838 hierarchical and 58 cross-tree", "36 and 34" | §5.3 selection criteria | sentence removed; letter quotes them |
| 95 s, 46 h, 1,752 QuickXplain runs | §5.3 limit paragraph | §6.1.1 states the limit **without figures**; letter quotes them |
| 4.1–4.3 h, 3.6×, "two and four days" | §5.3 n/a justification | §6.1.3 says "would exceed the compute budget"; letter quotes them |
| 515 / 92 / 6 / 613 / 194, γ = 203, bound ≈ 625 | §5.5.1 read-aloud | cells survive in Table 9; the sentence, γ and the bound do not; letter quotes them |
| FF safety bound of 10n | §5.4 | sentence removed. **Not named as letter-quoted** — kept as the generator's contract; Cowork to confirm |
| "a fresh solver per negative example" | §5.3 | sentence removed. Same status |

Relabelled in `revision_bias_composition`, `revision_ea2468_limit`, `revision_run_cost`,
`revision_order_and_working_example`, `revision_cabsc_condition` and
`check_paper_numbers.py`. Section citations that merely moved were renumbered:
S5.1→§5.1 (unchanged), S5.3→§6.1.1/§6.1.2, S5.4→§6.1.3, S5.5.1→§6.2.1, S5.5.3→§6.2.4,
S5.5.4→§6.2.3, S5.7→§6.4.

## Where this was done, and why not in the artifact

The brief says to branch off `bb508c0` in ConGenEvaluation. The change is **source code
that the artifact is carved from**: `release/README.md` §1 fixes the direction as
AcqMSS → artifact and never the reverse, and the next carve would overwrite anything
committed artifact-side. So the work is committed in AcqMSS and the artifact branch is
**derived**: carve from the AcqMSS commit, lay the carved tree over a clone at `bb508c0`,
commit as `r1-minimal-review`. The branch's diff is therefore exactly the artifact-visible
change, and re-carving reproduces it. `v1.0.0` untouched.

## Delivered

| what | where |
|---|---|
| development branch (source of truth) | AcqMSS `feat/sosym-r1`, head `95162ae` |
| artifact branch | ConGenEvaluation **`r1-minimal-review`** = `e51d72c`, one commit off `bb508c0` |
| `main` | `bb508c0`, untouched |
| `v1.0.0` | `bb508c0`, untouched |

Verified in the carve before pushing: `reproduce_tables_sosym.sh` exit 0 with a clean
`git status` afterwards, **334** gate checks, **1,305** cells 0 mismatched, coverage gate
green, **342** tests passed, six hygiene checks. Here: 339 checks, 681 passed / 1 skipped,
and all **234** revision assertions shown red on an altered value.

Also changed by the later items, after the first pass: Table 7 dropped "clauses of $B$"
(A5) and Table 11's first column became $|B'|$ (A6). `prose-reproduce-tables.patch` was
rebased, since the fragment count it carries in its own context moved from 12 to 11.

## Proposed tag for the re-carve

**`v1.0.1`.** The data is unchanged and every number still reproduces; what changed is
how the tables are laid out and how much of the paper the gate holds. That is a patch,
not a new dataset. The carve must be re-run on the tag day whatever the name: the hygiene
gate refuses a `CITATION.cff` whose `date-released` is not that day.

## Follow-up pass (same branch, re-carve, no tag)

| item | done |
|---|---|
| 1. Table 12 KB label as `\multirow{6}{*}{$KB_k$}`, KB5's n/a rows inside the group | yes |
| 2a. §6.2.4 equivalence sentence gone — check relabelled to §6.4 "1 of the 84 folds"; the unit `REAL-FM-7 rs_3n` fold 2 kept, labelled as quoted by the response letter | yes |
| 2b. "semantic precision stays below 1 on all 28 combinations" | yes, 28 rows, max **0.9943** at busybox 2-COV |
| 3. FF 10n bound and one-solver-per-negative as generator contracts, no section reference | yes — **they did not exist**, see below |
| 4. FLAMA | closed, no check added, not re-raised |
| 5. `tab_iterative_semantic`, `tab_rule_learners` | untouched |

**Per fold the precision claim does not hold, and it is reported rather than gated.**
Exactly **1 of 84** folds reaches semantic precision 1.000 — `REAL-FM-7 rs_3n` fold 2,
which is also the only exactly-equivalent fold and the only fold with semantic F1 =
1.000. All 28 combination means stay below 1, which is what the paper claims.

**Item 3 found nothing to relabel.** Neither the FF 10n bound nor "a fresh solver per
negative example" was ever in the gate — both were verified by reading in round 8 and
recorded in a report, which is not the same thing. They are now checks, in
`generator_contracts.py`, carrying no section reference. The solver contract is asserted
**behaviourally**: `build_checker` is wrapped in GenerateNE's own namespace and the
count compared with the number of negatives (9 for 9 on KB₁ 2-COV). A source-shape
assertion would pass a refactor that moves the call out of the loop but keeps the text.

The paper's tier sentence also changed shape — "the semantic F1 is at least as high as
the clause-based one, and both exceed the description-based one" — so the single
`Desc <= Clause <= Sem` chain is now three checks: one non-strict, two strict. A chain
would have stayed green if only the strict half failed.

## Per-table body diff against `main-r1.tex`

Whitespace-normalised, comments and rules dropped, column spec compared:

| fragment | verdict |
|---|---|
| `tab_fm_summary` | identical, 6 rows, `lrrrl` |
| `tab_example_sizes` | identical, 8 rows, `lrrrrrrrrrr` |
| `tab_AcqMssruntime` | identical, 31 rows, `llrrrrr` |
| `tab_accuracy_all` | identical, 7 rows, `lccccc` |
| `tab_comparison_strategies` | identical, 32 rows, `llrrrrr` |
| `tab_kb_size` | identical, 9 rows, `lrrrrrrrrrr` |
| `tab_iterative_accuracy` | identical, 19 rows, `llrrrrr` |
| `tab_runtime_comparison` | identical, 19 rows, `llrrrrr` |
| `tab_significance` | identical, 6 rows, `lrrrrl` |
| `tab_iterative_semantic` | **differs** — fragment is KB-as-column-groups (`llrrlrrlrrlrrlrrl`, 20 rows), manuscript is Strategy × Method (`llrrrrr`, 19 rows) |
| `tab_rule_learners` | **differs** — fragment is one row per KB with 20 value columns, manuscript is one row per (KB, strategy, learner), 25 rows, `lllrrrr` |

**Nine of eleven are identical to what the paper prints**, including all four changed
today. The two that differ are the two declared out of scope, and the difference is
layout, not values — which is what "pre-existing" predicted, now measured rather than
assumed.

This comparison is the link nothing else holds: `check_paper_tables.py` holds the
fragment to the data, and the manuscript transcribes the fragment by hand because the
journal template forbids `\input`. It ran from a scratch script against the manuscript
path. It could be a development-side gate — it cannot be an artifact-side one, since the
artifact has no manuscript.

## Follow-up 2 (S6.2.5 tables)

| item | done |
|---|---|
| 1. Tables 13 and 15: `\multirow{3}{*}` per strategy, `\midrule` between the six groups | yes |
| 2. Table 14 absorbs the queries table: `ll` + `rr`×5, empty ConGen q cells, plain q numbers, n/a spanning both columns, bold unchanged | yes |
| 3. Table 16: manuscript layout, `lllrrrr`, one row per (KB, strategy, learner), only the 8 scored combinations | yes |
| 4. `tab_significance` kept, marked artifact-only, checks relabelled to §6.2.5; claim 3's 28/28 and p < 10⁻⁷ for 1a, 1b, 3, 5 | yes |
| 5. Table 14's caption: stopping rules per fold, and the two budgets | yes |
| 6. Queries checks now cite Table 14 | yes |
| 7. Manuscript diff as a dev-side check | yes, `apps/sosym_r1/check_manuscript_tables.py`, never listed for the carve |
| 8. No other §6.2.5 sentence gated | respected |
| 9. Tag | on hold |

**Item 5 was already half-gated and half-missing.** The counts (66 `max_queries`, 18
`no_query`, 84 `pool_exhausted`) were asserted; the caption's claim is about *which*
fold stopped how, and a total cannot tell "all 18 KB₁ folds" from "18 folds scattered
anywhere". Now checked per fold, and the budgets are read from the folds that hit them
rather than from a constant — a re-run at another cap moves the check instead of
passing it.

**A pre-existing defect, found while editing:** `check_paper_tables.py` defined
`check_iterative_accuracy`, `check_iterative_semantic`, `check_runtime_comparison` and
`check_rule_learners` **twice**, the second shadowing the first. The copies were
byte-identical, so nothing had gone wrong yet — but I was about to edit them, and an
edit to the dead copy would have been silent. The 73 dead lines are removed. Present
since at least `c550b50`.

`MINIMUM_CELLS` 1000 → 900: the two rewritten tables print 354 fewer cells (the stop
column, and a rule-learner grid that was mostly "too few" markers). The combinations
that are no longer printed are still checked — the scored set is re-derived and the row
count asserted against it — so the fall is in printed cells, not in facts held.

### Per-table diff against `main-r1.tex` after this pass

```
tab_AcqMssruntime           identical (31 rows, llrrrrr)
tab_accuracy_all            identical  (7 rows, lccccc)
tab_comparison_strategies   identical (32 rows, llrrrrr)
tab_example_sizes           identical  (8 rows, lrrrrrrrrrr)
tab_fm_summary              identical  (6 rows, lrrrl)
tab_iterative_accuracy      identical (19 rows, llrrrrr)
tab_iterative_semantic      identical (20 rows, llrrrrrrrrrr)
tab_kb_size                 identical  (9 rows, lrrrrrrrrrr)
tab_rule_learners           identical (25 rows, lllrrrr)
tab_runtime_comparison      identical (19 rows, llrrrrr)
tab_significance            not printed (declared artifact-only)
```

**Eleven of eleven as expected: ten identical, one declared.** The check was shown red
first — one altered cell in `tab_fm_summary` gives exit 1 and a unified diff; exit 0
after regeneration.

## Unresolved

1. The FLAMA version sentence (finding 5). Needs a paper decision before it can be gated.
2. Whether the FF 10n bound and the fresh-solver sentence are quoted in the letter. If
   not, their checks describe the implementation rather than the paper, which is a
   different contract and should be said in their docstrings.
3. The per-phase durations are now computed, scope-checked, and printed nowhere. If they
   should stay visible, the fragment header comment is the place — it already documents
   their derivation.
