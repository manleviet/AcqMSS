# B′ scored as the CABSC condition, and the paper's identification claim decided

- Date: 2026-09-22
- Branch `feat/cabsc-condition-mss-scoring`, off `a1fd276` — the tree that carved v1.0.0 (`4dece76`)
- Code `apps/sosym_r1/measure_mss_as_cabsc_condition.py` · Data `data/results_sosym_r1/cabsc_condition/cabsc_condition.json`
- **84 of 84 folds measured. busybox completed; nothing was stopped, nothing estimated.**
- Baseline before any change: `pytest tests/ -q` → **no red test names** (681 passed, 1 skipped)

## Task 1 — B′ scored beside the delivered KB

B′ = `kb_constraints ∪ redundant_constraints`, gated against `n_mss` on every fold (84/84
agree, no fold skipped). Scored through `KBComparator`, the comparator the paper's tables
use. Means over the three folds; semantic tier.

| KB | Strategy | \|KB\| | \|B′\| | KB P | KB R | KB F1 | B′ P | B′ R | B′ F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| KB₁ | RS(n) | 18 | 92 | 0.778 | 1.000 | 0.875 | 0.415 | 1.000 | 0.585 |
| KB₁ | RS(2n) | 19 | 69 | 0.817 | 1.000 | 0.899 | 0.715 | 1.000 | 0.832 |
| KB₁ | RS(3n) | 13 | 62 | 0.931 | 0.985 | 0.957 | 0.932 | 1.000 | **0.964** |
| KB₁ | RS(m) | 18 | 132 | 0.685 | 0.894 | 0.775 | 0.236 | 1.000 | 0.381 |
| KB₁ | 2-COV | 9 | 294 | 0.775 | 0.939 | 0.849 | 0.086 | 1.000 | 0.158 |
| KB₁ | FF | 16 | 133 | 0.742 | 1.000 | 0.852 | 0.243 | 1.000 | 0.388 |
| KB₂ | RS(n) | 131 | 225 | 0.897 | 1.000 | 0.946 | 0.824 | 1.000 | 0.904 |
| KB₂ | RS(2n) | 135 | 216 | 0.884 | 1.000 | 0.938 | 0.839 | 1.000 | 0.912 |
| KB₂ | RS(3n) | 136 | 201 | 0.907 | 1.000 | 0.951 | 0.888 | 1.000 | 0.940 |
| KB₂ | RS(m) | 108 | 344 | 0.885 | 1.000 | 0.939 | 0.625 | 1.000 | 0.769 |
| KB₂ | 2-COV | 104 | 458 | 0.765 | 1.000 | 0.867 | 0.476 | 1.000 | 0.645 |
| KB₂ | FF | 121 | 269 | 0.848 | 1.000 | 0.918 | 0.709 | 1.000 | 0.830 |
| KB₃ | RS(n) | 177 | 541 | 0.500 | 0.969 | 0.660 | 0.234 | 1.000 | 0.380 |
| KB₃ | RS(2n) | 243 | 371 | 0.411 | 0.985 | 0.580 | 0.341 | 1.000 | 0.508 |
| KB₃ | RS(3n) | 224 | 314 | 0.430 | 0.967 | 0.596 | 0.400 | 1.000 | 0.572 |
| KB₃ | RS(m) | 74 | 1,167 | 0.685 | 1.000 | 0.806 | 0.103 | 1.000 | 0.187 |
| KB₃ | 2-COV | 48 | 1,375 | 0.767 | 0.746 | 0.705 | 0.096 | 1.000 | 0.174 |
| KB₃ | FF | 102 | 853 | 0.581 | 0.982 | 0.727 | 0.145 | 1.000 | 0.253 |
| KB₄ | RS(n) | 243 | 715 | 0.704 | 0.974 | 0.817 | 0.488 | 1.000 | 0.655 |
| KB₄ | RS(2n) | 249 | 565 | 0.779 | 1.000 | 0.875 | 0.627 | 1.000 | 0.770 |
| KB₄ | RS(3n) | 237 | 509 | 0.812 | 1.000 | 0.896 | 0.694 | 1.000 | 0.818 |
| KB₄ | RS(m) | 222 | 1,421 | 0.672 | 1.000 | 0.803 | 0.261 | 1.000 | 0.414 |
| KB₄ | 2-COV | 138 | 1,679 | 0.872 | 1.000 | 0.930 | 0.244 | 1.000 | 0.390 |
| KB₄ | FF | 230 | 869 | 0.683 | 1.000 | 0.811 | 0.410 | 1.000 | 0.580 |
| KB₅ | RS(n) | 687 | 2,543 | 0.809 | 0.998 | 0.894 | 0.763 | 0.998 | 0.865 |
| KB₅ | RS(m) | 485 | 4,637 | 0.829 | 1.000 | 0.907 | 0.293 | 1.000 | 0.453 |
| KB₅ | 2-COV | 7 | 6,634 | 0.994 | 1.000 | 0.997 | 0.184 | 1.000 | 0.311 |
| KB₅ | FF | 647 | 3,576 | 0.803 | 1.000 | 0.891 | 0.429 | 1.000 | 0.600 |

Description and clause tiers came free and are in the JSON; they are not reproduced here.

**What it says.** The CABSC condition recovers essentially everything — semantic recall
**1.000 on 81 of 84 folds**, against the delivered KB's 67 — and pays for it in
precision on every cell. It delivers **1.36× to 1,659×** as many constraints as the
theory ConGen ships. Semantic F1 delta (B′ − KB): median **−0.221**, min −0.758, max
**+0.023** (KB₁ RS(3n) fold 1, the one fold where B′ wins: its extra constraints happen
to be entailed, so recall rises to 1.000 with precision unchanged).

### The prediction was half right, and the half that failed is informative

> *Predicted:* on folds where NE is absent, the delivered KB must be logically
> equivalent to B′ and its semantic scores must be identical.

- **Equivalence: upheld, and stronger than predicted.** Measured directly, not inferred
  from a score: `KB ∪ NE ∪ BG ≡ B′ ∪ NE ∪ BG` on **84 of 84** folds. Reduce never
  changed the theory.
- **Identical scores: falsified.** Semantic *recall* moved on 14 folds and *precision*
  on 82. This is not a defect in Reduce. Semantic precision counts the delivered
  **clauses** that the target entails, so a redundant clause the target does not entail
  still counts against it — equivalence pins recall and leaves precision free. Recall
  moves only where NE was load-bearing: the tiers exclude the memorized ¬e⁻ from both
  sides, so a constraint Reduce dropped *with NE's help* leaves the scored KB weaker
  than B′. `recall(B′) ≥ recall(KB)` on all 84 folds.

### A correction to the prompt's framing

The prompt keys the prediction on `len(ne_constraints) == 0` (30 folds). That field is
the NE that **survived Reduce**, not the NE that Reduce and AcqMss saw. The folds where
NE was genuinely absent are those with no training negative: **5 of 84**, not 30. On the
other 25, NE was present and was dropped as redundant. The equivalence check above is
keyed on neither — it puts NE on both sides, which is how the run assembled the theory.

## Task 2 — the identification claim, decided

> *main-r1.tex:* "For complete positive examples A is exactly the subset AcqMss returns."

A recomputed per fold as `{c ∈ B : c accepts every training e⁺}`, by clause evaluation —
exact, because every example in this evaluation is a complete assignment (the script
asserts it rather than assuming it).

- `B′ ⊆ A` on **84 of 84** folds. The containment direction never fails.
- `A ⊋ B′` on **11 of 84** folds, each by exactly one constraint (10 distinct:
  c35, c212, c271, c274, c283, c673, c828, c1351, c2016, c2627).
- **The 11 are exactly the 11 folds with zero training positive examples** — set
  equality, not overlap. All are 2-COV cells, on all five knowledge bases.
- Equivalently: **A = B′ on every one of the 73 folds that has a positive example.**

**So the sentence is an over-claim only where it is vacuous.** With E⁺ = ∅ every
constraint accepts every member of an empty set, so A degenerates to the whole bias
(`|A| = |B|` on all 11), while AcqMss still returns `|B| − 1`.

The removal is not NE excluding a constraint, which was the expected mechanism and is
refuted: on KB₁ 2-COV fold 0, `SAT(c212 ∪ NE)` is **true** — c212 is consistent with the
six NE constraints GenerateNE produced there. The MSS condition is **set-level**, and
with no positive example it is vacuously satisfied, so it constrains nothing:
`SAT(B ∪ NE) = false`, and `SAT(B′ ∪ NE ∪ BG) = false` too. Neither A nor B′ is a
satisfiable theory on those folds. The one-constraint difference is where the recursion
bottoms out, not a semantic exclusion.

Method for that probe: recompute the fold's training split, run `ConGenTaskPreparation`
to get the NE assumption ids, resolve each to its blocking clause the way
`congen_model.py` does when it assembles the delivered theory, and solve. Scratch, and
reconstructable from this paragraph.

## What the Cowork layer can say

- **"CABSC was evaluated"** — yes, on all 84 folds, under the identification the paper
  already proves, with the table above.
- **The §2 clause "which is the subset AcqMss returns for complete positive examples"**
  needs one scope: it holds wherever E⁺ is non-empty, which is 73 of 84 folds, and is
  vacuous on the other 11. Suggested: "…for complete positive examples, of which at
  least one must be given".
- **The honest framing of the result** is not "CABSC is worse". B′ and the delivered KB
  are logically equivalent theories on every fold; they differ in how many constraints
  carry those semantics. CABSC returns the admissible pool; Reduce is what turns it into
  something a maintainer can read, at no semantic cost and at a large precision gain.
  The tiers measure delivered form, and that is the whole of the difference.

## Runtime

No casualty. busybox (|B| = 6,635, up to 6,634 constraints scored per fold with
per-clause bidirectional entailment) finished all 12 folds; the full 84-fold pass runs in
minutes, because no acquisition is re-run and A needs no solver.

## Unresolved

1. Whether the §5.2 sentence should also state that the CABSC condition attains recall
   1.000 on 81 of 84 folds. It is the strongest thing measured here and it is not in the
   prompt's plan for the paragraph.
2. On the 11 zero-positive folds neither A nor B′ is satisfiable together with NE. The
   paper treats 2-COV as the degenerate regime already (§5.5.5); whether this specific
   fact belongs in §5.7 as a threat is a Cowork decision.
3. `n_mss` counts B′ *before* Reduce and is reported nowhere in the paper. If the §5.2
   sentence quotes \|B′\|, the number needs a home in a table or the text.
