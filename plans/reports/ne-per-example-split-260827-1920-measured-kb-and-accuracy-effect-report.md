# What the per-e⁻ NE split actually does, measured on 72 folds

Date 2026-08-27. Branch `feat/sosym-r1`. Code under test, all UNCOMMITTED: NE negation
fix (a) + C12 + the per-e⁻ split (b) in `conacq/algorithms/acqmss/`, plus `ne_clauses`
and `redundant_ne_constraints` added to the CV fold dict.

Method: re-ran the ConGen sweep with (a)+C12+(b) into a scratch directory
(`tools/sosym_r1/measure_ne_per_example.py`, always `-o`, `data/` verified clean before
and after), then measured the accuracy effect on the same folds
(`tools/sosym_r1/measure_ne_accuracy_effect.py`). 24 cells, 72 folds, 4 knowledge bases.
**busybox is NOT covered** — 12 folds, 12.73 h of the ledger's 14.89 h, needs a night
window. Every statement below is scoped to the 72.

Predicting `n_ne` from the root-dependence classification was never cheaper than
measuring it: the classification needs B′ per fold, which is the same run.

## Table 1 — n_ne per fold

| | n_ne = 0 | n_ne = 1 | n_ne > 1 |
|---|---|---|---|
| committed (combined) | 5 | 67 | 0 |
| with (b) (per-e⁻) | 30 | 42 | **0** |

**Maximum n_ne under (b) across all 72 folds is 1.** It rises on zero folds and falls
on 25. Of the 67 folds with training negatives, 42 keep exactly one ¬e⁻ and 25 keep none.

810 ¬e⁻ prepared, **42 retained, 768 discarded**, and the accounting closes on every
fold — `n_ne + discarded = |E⁻|`, 0 violations in 72.

Why the count collapses rather than climbing toward |E⁻|: memorized ¬e⁻ facts entail
each other through B′. Measured on arcade `rs_1n` fold 0, whose four negatives reduce to
two distinct minimal conflicts:

    B' + [NOT(UninstallGame = false)] entails [NOT(UseCases = false)]?      YES
    B' + [NOT(UseCases = false)]      entails [NOT(UninstallGame = false)]? YES

`UseCases --mandatory--> UninstallGame` is a biconditional under FM semantics, so the
two conflicts are interderivable and exactly one survives — whichever Reduce tests last
(fold 0 keeps `UseCases`, fold 2 keeps `UninstallGame`; the order effect again).

**C6's premise survives (b) intact.** It was decided on "n_ne ∈ {0,1} … the whole
question is about exactly one constraint", and that remains true of every fold measured.
The reporting policy does not need reopening.

## Table 2 — |KB| = n_kb + n_ne, per knowledge base

| KB | folds | old \|KB\| | new \|KB\| | Δ | old n_ne | new n_ne | accuracy moved |
|---|---|---|---|---|---|---|---|
| REAL-FM-7 | 18 | 281 | 288 | +7 | 16 | 10 | 0/18 |
| arcade-game | 18 | 2603 | 2620 | +17 | 17 | 17 | 0/18 |
| fqa | 18 | 2213 | 2205 | **−8** | 17 | **0** | 0/18 |
| REAL-FM-4 | 18 | 3948 | 3971 | +23 | 17 | 15 | 0/18 |

Per fold: mean **+0.54**, range **[−3, +4]**. The movement is in `n_kb`, not `n_ne` —
discharging a ¬e⁻ removes something that was licensing the removal of bias constraints,
so a few more of those survive. fqa is the clean case: every conflict there is
root-independent, so all 17 ¬e⁻ are discharged and |KB| falls.

This is a materially different disclosure from the "+32 on one fold" that was feared.

## Table 3 — does any reported number move?

`cross_validation.py:210` builds `AccuracyCalculator`'s theory as
`kb_clauses + ne_clauses + bg_clauses`, citing Definition 6. On a fold with more than one
training negative the combined ¬e⁻ id resolved to a unit clause over an AUXILIARY
variable, constraining nothing over the feature vocabulary — so the theory scored was
effectively the theory without NE. Pre-existing (verified against reverted code, identical
numbers) and demonstrable: REAL-FM-7 `2cov` delivers a theory accepting 2 of 9 TRAINING
negatives, a Definition 6 violation.

But the tables report TEST-fold accuracy. Measured per fold, same learned KB, theory
scored with the real ¬e⁻ clauses versus without them:

| | folds |
|---|---|
| measured | 72 |
| reconstruction-control failures | **0** |
| **test-fold FP moves** | **0** |
| fold accuracy differs from committed | **0 / 72** |

The control is load-bearing: `kb_clauses` is rebuilt from `kb_constraints` via the bias
constraint map, and a fold whose rebuilt accuracy fails to reproduce the recorded one is
reported as a mismatch and nothing is claimed from it. Zero mismatches in 72.

**The defect is real and inconsequential to the tables.** No published accuracy figure
moves. Had it moved, the direction would have favoured ConGen — QuAcq delivers no NE, so
ConGen's theory was scored missing content QuAcq never had, biasing Table 13 against
ConGen. It did not move, so there is nothing to correct and nothing to claim.

Scope of the defect, verified in code rather than assumed: `kb_comparator.py:293` guards
clause and semantic scoring with `if self.bias.has_constraint(cid)`, and an NE has no bias
id. Description compares ids. So Desc/Clause/Sem and every F1 in Tables 10/11/14 are clean
of this defect; only accuracy was exposed, and it did not move.

## What (b) does repair

REAL-FM-7, delivered theory FP on training negatives, before → after (b):

| cell | \|E⁻\| | ne_clauses before | after | theory FP |
|---|---|---|---|---|
| `2cov` | 9 | `[[720]]` | `[[4, 3]]` | **2 → 0** |
| `ff` | 3 | `[[732]]` | `[[2]]` | 0 → 0 |
| `rs_3n` | 4 | `[[796]]` | `[[1]]` | 0 → 0 |

So (b) is not accounting tidiness: it repairs a Definition 6 violation in the delivered
theory. That, not the |KB| bookkeeping, is its justification.

## Unresolved

1. `exact_equiv` under (b) is not measured. It needs a `run_compare` scoring pass over
   the scratch CV files, which now carry `ne_clauses` — so `backfill_ne_clauses.py` is no
   longer needed for new runs, only for the committed ones.
2. busybox: 12 folds uncovered. Nothing above generalizes to it without measurement; its
   conflicts could be root-dependent in a different proportion.
3. Four goldens (plus `test_congen_ff_prepared_task_ids`, which (b) touches) stay red by
   design until re-frozen — after (b) lands, never before.
4. `kb_model.py:_resolve_fallback_clause` carries a NOTE stating multi-negative per-e⁻ ids
   are left unregistered in `describe`. (b) registers them; the note goes stale if (b) lands.
