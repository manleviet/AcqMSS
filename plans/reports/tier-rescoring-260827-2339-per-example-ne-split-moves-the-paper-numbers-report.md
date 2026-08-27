# The per-e⁻ NE split moves the paper's headline metrics

Date 2026-08-27. Branch `feat/sosym-r1`. Code under test, UNCOMMITTED: (a) NE negation +
C12 + (b) per-e⁻ split, `ne_clauses`/`redundant_ne_constraints` on the CV fold, repaired
NE fixtures, updated resolver NOTE. 72 folds, 4 knowledge bases, busybox NOT covered.

Supersedes the "no reported number moves" framing of the 19:20 report: that measured
ACCURACY, which is unaffected. The three tiers are scored from `kb_constraints`, and
`kb_constraints` moved.

## 1. arcade `rs_1n` fold 0 — the count is not the bundled count

Same integer, different object:

| | n_ne | the named object |
|---|---|---|
| committed | 1 | `(NOT(UninstallGame=false) AND NOT(UseCases=false) AND NOT(UninstallGame=false) AND NOT(UseCases=false))` |
| with (b) | 1 | `NOT(UseCases = false)` — plus 3 named in `redundant_ne_constraints` |

Per-e⁻ trace, `set_neg_tv = [4331, 4397, 4463, 4529]`, C12 order:

| id | conflict | verdict | discharged against |
|---|---|---|---|
| 4331 | `NOT(UninstallGame = false)` | REMOVED | not B′ alone; siblings 4397/4463/4529 present |
| 4397 | `NOT(UseCases = false)` | REMOVED | not B′ alone; siblings 4463/4529 present |
| 4463 | `NOT(UninstallGame = false)` | REMOVED | not B′ alone; sibling 4529 present |
| 4529 | `NOT(UseCases = false)` | **KEPT** | nothing left to entail it, and B′ alone cannot |

Not one of the three is discharged by B′ alone — every discharge needs a surviving
sibling. The two distinct conflicts are interderivable through B′, measured both ways:

    B' + [NOT(UninstallGame=false)] entails [NOT(UseCases=false)]?  YES
    B' + [NOT(UseCases=false)] entails [NOT(UninstallGame=false)]?  YES

`UseCases --mandatory--> UninstallGame` is a biconditional under FM semantics. Two
survivors was the wrong prediction for that reason, not because the measurement was
reporting a stale quantity.

## 2. The three tiers move — 155 of 216 metrics

`run_compare` re-scored all 24 CV files, one block per file (the `kb_dir` guard), then
each model's `summary` compared against the committed one. 24 models × 3 tiers × 3
metrics = 216 comparisons.

| | count | max abs delta |
|---|---|---|
| **moved** | **155 / 216** | **0.0909** |
| description | 49 | 0.0513 |
| clause | 52 | 0.0606 |
| semantic | 54 | 0.0909 |

Largest movers:

| model | tier | metric | old | new | Δ |
|---|---|---|---|---|---|
| REAL-FM-7_ff | semantic | recall | 0.9091 | 1.0000 | +0.0909 |
| REAL-FM-7_2cov | semantic | recall | 1.0000 | 0.9394 | −0.0606 |
| REAL-FM-7_rs_3n | clause | recall | 0.6818 | 0.7424 | +0.0606 |
| REAL-FM-7_2cov | semantic | f1 | 0.9047 | 0.8489 | −0.0558 |
| REAL-FM-4_rs_3n | semantic | recall | 0.9447 | 1.0000 | +0.0553 |
| arcade-game_2cov | clause | precision | 0.6549 | 0.6002 | −0.0547 |
| REAL-FM-4_2cov | semantic | recall | 0.9470 | 1.0000 | +0.0530 |

Second decimal, not third. Movement is mixed in sign; the largest negatives are on the
degenerate `2cov` cells (train_pos = 0). Small denominators amplify: REAL-FM-7 semantic
recall +0.0909 is +1/11.

**Attribution is NOT isolated.** The scratch run carries (a)+C12+(b) together. Fold-0
measurement on three cells showed (a)+C12 alone reproduces the committed result exactly
on arcade and REAL-FM-4 and changes only fqa, so most of this is presumably (b) — but
"presumably" is the word, and isolating it costs a second 2.2 h sweep with (b) reverted.

## 3. Exact equivalence — 1 / 72, and (b) created it

| run | exactly equivalent |
|---|---|
| committed | **0 / 72** |
| (a)+C12+(b) | **1 / 72** — `REAL-FM-7_rs_3n` fold 2 |

The committed side is scored bias + BG only, because the old schema has no `ne_clauses`;
that is the right comparison anyway, since the combined ¬e⁻ resolved to an auxiliary
clause that constrains nothing over the feature vocabulary.

The positive fold verified rather than reported: 11 bias constraints → 17 clauses, Cτ has
22, bidirectional entailment with 0 unentailed either way. Falsification — dropping any
single KB clause breaks equivalence on **14 of 17**, so the verdict tracks the KB. It is
also equivalent without the ¬e⁻ clause, because that fold's retained NE is `[[1]]`, the
root literal already present in BG.

A 1/72 is only meaningful because the scorer is known able to return 1:
`tests/test_semantic_scorer_positive_control.py` (6/6) feeds Cτ back and requires a
perfect score, then perturbs it and requires an imperfect one.

Committed `n_kb` on that fold is 9; with (b) it is 11. The two constraints (b) leaves in
place are what close the equivalence.

## 4. Test suite

`678 passed, 5 failed, 1 skipped`. The five are goldens frozen from pre-change code:
`test_congen_runner_result_is_pinned[None|42]`, `test_congen_{rs,ff}_learned_kb_identical`,
`test_congen_ff_prepared_task_ids`. Re-freeze after (b) lands, never before.

## Unresolved

1. **The re-run question is live again, and now for the right reason.** The tiers move in
   the second decimal, so the branch touches Tables 10/11/14. Whether that is a
   correction to publish or a change to reject is not a measurement question.
2. **Attribution between (a)+C12 and (b)** is not isolated across 72 folds. One more
   2.2 h sweep with (b) reverted would settle it, and it decides whether the disclosure
   names one change or three.
3. **busybox uncovered** — 12 folds, 12.73 h, night window. It is the KB where the root
   axiom's reach is largest, so nothing above transfers to it by inference.
4. Interactive/QuAcq CV files are not re-scored here; ConGen only.
