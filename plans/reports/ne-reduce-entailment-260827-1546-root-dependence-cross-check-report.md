# Why Reduce discharges NE on some folds and retains it on others

Date 2026-08-27. Branch `feat/sosym-r1`. Code under test: NE negation fix (a) in
`conacq/algorithms/acqmss/task_preparation.py::_create_negated_ne` plus C12 in
`conacq/algorithms/acqmss/reduce.py:78` — both UNCOMMITTED at time of measurement.
Probe: `ne_world.py` (scratch), fold 0 of each cell, same split/seed machinery as the
sweep (`apply_folds` + `fold_data.shuffle_seeds[i]`), glucose4 incremental.

## Question

With (a)+C12 applied, Reduce removed NE on fqa `rs_2n` and kept it on arcade `rs_1n`
and REAL-FM-4 `rs_3n`. Every ¬e⁻ had previously measured 100 % entailed by KB∖NE ∪ BG
on all four cells, so retention had no explanation.

## World 1: the model satisfies the examples

Reduce's test `consistent(BG ∪ (KB∖{NE}) ∪ {¬NE})` is SAT on arcade `rs_1n` fold 0.
Its model satisfies **all four** eᵢ, and picks `negated_ne_id 4532` (e1). So B′ does
not entail ¬eᵢ in Reduce's context. The encoding is correct — (a) asserts the example
and the assertion propagates. The entailment is simply absent.

## The two backgrounds

The measurement and Reduce run against different theories, by design and unnamed:

| | background | source |
|---|---|---|
| Reduce's redundancy test | `task.set_b` = `[]` | `task_preparation.py:183-186` — C7 moves root OUT of the acquisition BG into `root_axiom`, so `X → root` constraints stay learnable |
| delivered theory / entailment scoring | `bg_clauses` = root | `congen_model.py:96` (`bg_clauses = root_clauses`) |

Asserting `root_axiom` alongside flips Reduce's test to UNSAT on both retaining cells.

## Per-eᵢ entailment, both contexts

`SAT no-root` = B′ does NOT entail ¬eᵢ in Reduce's context. `SAT +root` = same with
root asserted. `SAT in both` would refute the mechanism; it occurs nowhere.

### fqa `rs_2n` fold 0 — |E⁻| = 23, |B′| = 209, **NE REMOVED**

23/23 root-independent (UNSAT in both contexts). Every minimal conflict is a pairwise
feature relation: `Usability=F, XML=T`; `SHA256=T, SHA512=T`; `Query=T, Store=T`;
`SocialID=T, UserPassword=T`; `SecureDatabase=T, Security=F`; …

### arcade-game `rs_1n` fold 0 — |E⁻| = 4, |B′| = 517, **NE KEPT**

| eᵢ | SAT no-root | SAT +root | verdict | literals |
|---|---|---|---|---|
| e0, e2 | True | False | root-dependent | `UninstallGame=F` |
| e1, e3 | True | False | root-dependent | `UseCases=F` |

4/4 root-dependent. Both conflicts are single-literal "a mandatory descendant of the
root is absent" — unentailed once nothing forces the root true. The model takes exactly
that escape: `ArcadeGame = False`, the empty product.

### REAL-FM-4 `rs_3n` fold 0 — |E⁻| = 58, |B′| = 502, **NE KEPT**

25 root-independent, 33 root-dependent, 0 unexplained. Mixed, and it is the cell that
sharpens the rule. Root-dependent conflicts are `eShop=F` (32×) and `Taxationoptions=F`
(1×, a mandatory child of root); root-independent ones are pairs such as
`Wishlist=F, Wishlistsaveaftersession=T` and `Warehousemanagement=F, Weight1=T`.

## The rule

NE is prepared as ONE combined assumption (a conjunction), so ¬NE is the disjunction
of the eᵢ. The test is therefore SAT iff **any** eᵢ is satisfiable:

> Reduce discharges NE iff **every** eᵢ's minimal conflict is root-independent.
> One root-dependent conflict retains the whole combined NE.

Holds on 3/3 cells: fqa 0 root-dependent → removed; arcade 4 → kept; REAL-FM-4 33 →
kept. This is a per-fold falsifiable prediction, not a summary.

## Decision (Viet-Man, 2026-08-27): Reduce stays root-free

Asserting root only for the NE test would treat one constraint differently inside a
loop Algorithm 3 writes as uniform — unexpressible in the pseudocode, i.e. an
implementation secret. Asserting root for everything reverses C7 and reinstates the
defect it fixed: every `X → root` becomes BG-entailed, Reduce drops it, recall is
understated on exactly those constraints. Current behaviour is coherent: Reduce reasons
in the acquisition context, that context excludes root so root-implied constructs stay
learnable, and an NE whose conflict turns on root is not provably redundant there, so
it is retained. The guarantee stands where it cannot be discharged.

(a) + C12 are correct and stay. The fix stops here.

## Disclosure wording this supports

Reduce discharges NE where the acquisition background proves it redundant and retains
it otherwise; because the root axiom is deliberately excluded from that background so
root-implied constraints remain learnable, NE is retained on knowledge bases whose
negative examples turn on root.

## Unresolved

1. Part (b) — NE passed to Reduce as n separate constraints — now has a predicted,
   non-zero effect: on REAL-FM-4 `rs_3n` fold 0, 25 of 58 per-e⁻ NEs would be
   discharged individually while 33 survive; under the combined encoding all 58 ride on
   one retained object. Earlier note "on our data (b) changes no number" was recorded
   before this measurement and is read here as scoped to the three scoring tiers, which
   exclude NE. Whether `exact_equiv` and accuracy move is untested.
2. Only fold 0 of three cells measured. The rule is stated per fold and should be
   checked across the 84-fold scan.
