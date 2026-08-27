# Red-team: the NE / root-dependence result

Adversarial review of everything claimed on 2026-08-27 about why Reduce retains NE.
Method: attack each claim with the control that would have exposed it, and run the
control. Code under test unchanged (uncommitted (a) + C12).

## Survived

**Reproduction.** Probe |B′| = 517 / 209 / 502 (arcade `rs_1n`, fqa `rs_2n`,
REAL-FM-4 `rs_3n`, fold 0) vs committed `n_mss` 517 / 209 / 502. Exact, 3/3. The probe
walks the sweep's path: `congen_model.py:53` shows `prepare_task` is literally
`ConGenTaskPreparation(profiler=…).prepare(...)`, which is what the probe calls.

**Assertions are not silently dropped.** `CheckerBase._compute_delta` (backend.py:59)
returns `set_c` unchanged as `enabled`; the per-eᵢ `neg_id` asserts reach the solver
even though they are not registered assumptions.

**Non-vacuity.** Control A `consistent(base)` = True and control B
`consistent(base + root_axiom)` = True on all three cells. Had B been False, every
"root-dependent" verdict would have been vacuous — root would have contradicted B′
outright rather than supplying the missing entailment.

**Encoding intact.** Control C: 0 of 85 eᵢ produced a model failing to satisfy its own
literals. Fix (a) asserts the example and the assertion propagates.

**Cited numbers.** "NE survived on all 79 folds that had negatives" — verified from
committed data: 84 folds, 79 with training negatives, NE kept on 79/79. "ConMin
assembles F → S → C" — verified at `conmin.py:257`.

## Broken

### F1 — my survivor counts were wrong; fix (a) alone changes nothing (self-correction)

Reported earlier: "survivor counts moved on all three cells — 170 / 241 / 137 against
172 / 235 / 135 — including where NE was kept… most movement comes from order rather
than the fix." Wrong, and wrong by a unit mismatch: 172 / 235 / 135 are `n_kb`, which
is **bias-only** under the C6 contract `|KB| = n_kb + n_ne`. The comparable committed
totals are 173 / 136 / 236.

Measured, running Reduce's loop in both orders off the same B′:

| cell | committed `n_kb`+`n_ne` | (a), NE last (pre-C12) | (a) + C12 |
|---|---|---|---|
| arcade `rs_1n` f0 | 173 | 173, NE KEPT | 173, NE KEPT |
| fqa `rs_2n` f0 | 136 | 136, NE KEPT | **137, NE REMOVED** |
| REAL-FM-4 `rs_3n` f0 | 236 | 236, NE KEPT | 236, NE KEPT |

Two consequences.

1. **Fix (a) on its own reproduces the committed result exactly on all three cells.**
   C12 is the entire behavioural effect — now measured, where it had only been reasoned
   from "Reduce tests against `kb_delta`".
2. **Nothing moves except where NE is discharged.** The blast radius is smaller than
   reported, not larger: folds whose conflicts are all root-independent lose their NE
   and gain the constraints NE was licensing the removal of (fqa: 135 → 137 bias).
   Folds with any root-dependent conflict are byte-identical.

The earlier figures 170 and 241 do not reproduce; 137 does. No attempt is made here to
explain where they came from — the current numbers carry a reproduction control (the
pre-C12 order reproducing committed on 3/3) and the earlier ones did not.

The separate order-sensitivity result — 10 permutations of Reduce's input → 10 distinct
survivor sets — is unaffected. It was measured independently. What is withdrawn is the
claim that **this** change exercised that sensitivity.

### F2 — NE retention is not what makes the theory reject the negatives

Control D: **0 of 4, 0 of 23, 0 of 58 full negative examples are accepted by B′ without
root.** B′ alone already rejects every training negative in Reduce's own context.

So retention is not the Definition 6 safety net firing. `generate_ne.py:171` minimizes
each e⁻ with QuickXplain, so the encoded eᵢ is a **partial** assignment and ¬eᵢ is a
strictly **stronger** claim than ¬e⁻ — "no product may have `UseCases=False`", not "not
this product". Reduce asks whether the *generalization* is entailed; it is not, without
root. The specific example is entailed-rejected either way.

Caveat on scope: D is measured at B′, not at the delivered post-Reduce KB. Whether the
delivered KB still rejects them without NE is a different question and is exactly what
NE is retained to guarantee. So this does not license removing NE — it corrects what
retention *means*, and it removes "needed for Definition 6" from the disclosure.

### F3 — 7 red tests, attributable; 3 are a coverage regression

`674 passed, 7 failed, 1 skipped` with (a) + C12 (uv, `--no-sync`). Substitution check:
reverting the three files and re-running exactly those 7 → **7 passed**. So the red set
is attributable to the change and nothing else. Zero ConMin failures despite (a)
touching `conmin/task_preparation.py`.

Four are goldens frozen from pre-change code and must be re-frozen:
`test_congen_runner_result_is_pinned[None|42]`, `test_congen_{rs,ff}_learned_kb_identical`.

Three fail on **fixture preconditions**, not assertions: "expected at least one
memorized ¬e⁻ on rs_1n", "fixture must memorize at least one ¬e⁻", "fixture must keep
the NE, to then drop it". Their fixtures assumed the defect — NE always survived. The
C6 contracts they cover (`test_ne_split_out_of_kb_names`,
`test_delivered_theory_carries_the_memorized_negatives`,
`test_ne_accounting_closes_when_reduce_discards_an_ne`) are now **untested**, which is a
coverage regression that must be repaired with a root-dependent fixture before landing —
not by relaxing the tests.

## Minor

- The C12 comment in `reduce.py` states "~345 of 517 constraints are already gone by the
  time NE is reached" as measured, without naming the cell. It is arcade `rs_1n` fold 0.
  Name it or drop the figure.
- The rule "Reduce discharges NE iff every eᵢ is root-independent" is a **theorem** of
  the encoding, not an empirical finding: ¬NE is the disjunction of the eᵢ
  (`task_preparation.py:336`), so the test is SAT iff some eᵢ is satisfiable. The 3
  cells are a consistency check. What is genuinely falsifiable per fold is the
  root-dependence classification, not the iff.
- Both reports cite line numbers in uncommitted files; they will drift.

## Unresolved

1. Repair the three fixture-precondition tests with a root-dependent cell so the C6
   contracts stay covered. Blocks landing.
2. Re-freeze the four goldens — after (b), not before, or they get frozen twice.
3. F2 changes the case for part (b): discharging root-independent per-e⁻ NEs
   individually now looks like removing a *generalization* the KB does not entail,
   which is a stronger claim than tidying accounting. Worth deciding before implementing.
4. Fold 0 only, three cells. The 84-fold scan is the breadth check.
