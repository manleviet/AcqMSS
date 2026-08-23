# C4 — rule-learner baselines (RIPPER / CN2 / decision tree)

- Status: **PLAN — awaiting approval. No code written.**
- Branch: `feat/sosym-r1`, base `f3aeb27`
- Scope: three rule learners as a comparison baseline; rule set → CNF → existing scorers.
- Out of scope: choosing which learner goes in the paper (decided later, on pre-declared criteria).

## Answers to the five questions

### 1. Three learners, three converters? — **No. Two.**

| learner | native output | conversion |
|---|---|---|
| RIPPER (`wittgenstein`) | ordered rule list, each rule a conjunction of literals | **converter A** |
| CN2 (`Orange3`) | ordered rule list, each rule a conjunction of selectors | **converter A** |
| decision tree (`scikit-learn`) | binary tree | **converter B** = enumerate root→leaf paths whose leaf predicts *invalid*, each path is a conjunction → then converter A |

Converter B is a *reduction*, not a parallel implementation: it turns a tree into the same
"list of conjunctions over feature literals" that A consumes. So one CNF core, two front
ends. Claim to verify at implementation time, not assumed: that CN2's selectors on a purely
binary table are only `f == 0` / `f == 1` and never a range or set-membership operator. If
Orange emits anything else, CN2 needs its own literal extractor (still feeding converter A).

The CNF core is trivial *because the positive class is `invalid`*:

```
rule set = DNF for "invalid"
valid(x) ⟺ no rule fires ⟺ ⋀ᵢ ¬(lᵢ₁ ∧ … ∧ lᵢₖ) = ⋀ᵢ (¬lᵢ₁ ∨ … ∨ ¬lᵢₖ)
```

One clause per rule, no Tseitin, no auxiliary variables. Learning the `valid` class instead
would give a DNF needing real encoding — not done.

### 2. Feature table and the literal → variable-id mapping

Table: rows = `E⁺ ∪ E⁻` for the fold's **training** split; columns = the FM's features, in
`model.name_to_id` order; cell = the boolean from `assignments`; label = `1` for `e⁻`
(invalid), `0` for `e⁺`. Source is `data/examples/*.json`, `positive[i].assignments` /
`negative[i].assignments` — every example carries a **complete** assignment over all
features (verified on `REAL-FM-7_rs_1n`: 14 keys, all features present), so no missing-value
handling is needed.

Mapping back: feature name → `model.name_to_id[name]`; literal is `+id` when the rule tests
`true`, `-id` when `false`. Negating for the CNF clause flips the sign.

**Where this goes wrong silently, and how it is caught.** Column order and id order are
independent — `name_to_id` comes from flamapy's tree traversal, not alphabetical (a
documented repo gotcha). A converter that pairs column *index* with variable *id* produces a
consistent-looking CNF over permuted variables: every downstream call still succeeds,
accuracy lands somewhere plausible, and nothing raises. Three guards, none of which is
"the suite is green":

1. The converter never sees column indices. It maps by **name**, and the round trip
   `id → name → id` is asserted on construction.
2. A permutation canary: build the table with columns deliberately reversed, learn, convert,
   and assert the resulting CNF is **identical** to the un-permuted run. Index-pairing fails
   this; name-pairing passes.
3. Every literal emitted must satisfy `abs(lit) in name_to_id.values()`, asserted in the
   converter rather than left to a downstream crash.

### 3. Library versions and `pyproject.toml`

**None of the three are installed, and neither are `numpy`, `pandas` or `scikit-learn`.**
The current runtime deps are `flamapy-*`, `python-sat`, `toml`, `allpairspy`, `PyYAML` — no
scientific stack at all. So C4 is not "add three packages", it is "introduce a scientific
stack to a lean repo".

Transitive weight, heaviest last:

| package | pulls in | note |
|---|---|---|
| `scikit-learn` | numpy, scipy, joblib, threadpoolctl | the tree; smallest of the three |
| `wittgenstein` | pandas, numpy | RIPPER/IREP |
| `Orange3` | numpy, scipy, scikit-learn, bottleneck, pyqtgraph, AnyQt, serverfiles, … | a full GUI data-mining suite; by far the largest |

**Proposal: a single `baselines` extra, not runtime deps.**

```toml
[project.optional-dependencies]
baselines = ["scikit-learn", "wittgenstein", "Orange3"]
```

Rationale: the acquisition pipeline and the whole sweep must keep installing from a clean
environment without any of this. Putting Orange3 in `dependencies` makes a headless sweep
machine build a Qt-adjacent stack it never runs. Versions get pinned to whatever resolves at
implementation time and recorded here — not guessed now.

Baseline code imports these **lazily inside the learner adapters**, so `pytest tests/` on a
machine without the extra skips the C4 tests rather than failing at import. Same shape as the
existing fixture-missing skips.

### 4. Tests that prove the converter correct

Minimum, as required:

- **Hand-built rule set → hand-written CNF.** Two rules over three features, expected clauses
  written by hand, compared with `SemanticEquivalenceChecker` (`conacq/eval/semantic_equivalence.py:48`,
  bidirectional entailment) rather than by list equality — so a different but equivalent
  clause ordering passes and a genuinely different theory fails.
- **Empty rule set ⇒ empty CNF ⇒ accepts everything.** This is the degenerate case §5 shows is
  frequent, so it must be pinned deliberately rather than met by accident.
- **Single-literal rule** ⇒ single unit clause with flipped sign (catches a missing negation,
  which an all-conjunctions fixture can hide).
- **Permutation canary** (§2) — the guard for the failure mode that leaves tests green.
- **Tree front end**: a hand-built 2-level tree with one `invalid` leaf ⇒ the same CNF as the
  equivalent one-rule rule set, i.e. converter B composed with A agrees with A directly.

### 5. Time estimates

Learners train on the **example table only** — tens to hundreds of rows, ≤ ~2.5k features
(REAL-FM-4) — and never touch the bias or a solver. Expect **seconds per fold**, dominated by
imports. If any learner takes minutes, something is wrong (most likely: the bias got into the
table).

| item | estimate |
|---|---|
| dependency setup + version pinning | 0.5 h |
| feature-table builder + id mapping | 1 h |
| converter A (rules → CNF) + tests | 1.5 h |
| converter B (tree → rules) + tests | 1 h |
| three learner adapters | 1.5 h |
| eval wiring (folds, scoring, CSV columns) | 2 h |
| full 3-KB × 6-sampling × 3-fold run | < 10 min |
| **total** | **~7.5 h**, run time negligible |

## §5 — the finding that should gate approval

**The target class is nearly empty, and on several cells it is exactly empty.**

Positive class = invalid = `E⁻`. Training split is ⅔:

| KB | sampling | E⁻ total | E⁻ in training |
|---|---|---|---|
| REAL-FM-7 | rs_1n | 1 | **0** |
| REAL-FM-7 | rs_m | 1 | **0** |
| REAL-FM-7 | rs_2n | 2 | 1 |
| REAL-FM-7 | rs_3n | 4 | 2 |
| REAL-FM-7 | ff | 3 | 2 |
| arcade-game / fqa / REAL-FM-4 | rs_m | 1 | **0** |
| REAL-FM-7 | 2cov | 9 | 6 — but **E⁺ = 0** |
| fqa | 2cov | 16 | 10 — but **E⁺ = 0** |

Consequences, which are results rather than bugs but must be declared, not discovered:

- **Zero training negatives** ⇒ no instance of the class being learned ⇒ every learner returns
  an empty rule set ⇒ CNF = ∅ ≡ ⊤ ⇒ the theory accepts everything: accuracy = the positive
  fraction of the test fold, semantic recall 0, specificity 0.
- **Zero positives (2COV)** ⇒ the other class is empty; RIPPER and CN2 will emit either
  nothing or a single always-fire rule ⇒ theory ≡ ⊥, rejecting everything.
- The cells with any signal at all are the larger samplings on fqa / REAL-FM-4 / arcade-game.

So a full 3×6 baseline table is mostly structurally-determined cells. That is defensible and
arguably the point — it shows a rule learner cannot work from this example budget while
ConGen can — but it is a different claim from "we compared against a rule-learner baseline",
and the table should be read as the former.

**Decision this gates:** if the intended claim needs cells with actual learned rules, C4 needs
either more negatives per fold or a restriction to the samplings that have them, and that is a
sweep-scope change. If the degenerate cells are acceptable as evidence, C4 proceeds as
specified.

## Sequencing

1. deps + `baselines` extra (own commit)
2. feature table + id mapping + permutation canary (own commit)
3. converter A + tests (own commit)
4. converter B + tests (own commit)
5. three adapters (own commit)
6. eval wiring + the 3-KB run (own commit)

Steps 2–4 are gated by tests that do not need any learner installed, so they stay verifiable
on a clean machine.

## Unresolved

1. **Does the degenerate-cell finding change the intended claim?** (§5) — the one question that
   should be settled before any code.
2. Orange3 in a `baselines` extra vs dropping CN2 entirely. Orange3 is disproportionately heavy
   for one learner; if CN2 is not load-bearing for the paper, dropping it removes the largest
   dependency and one front end.
3. Whether the baseline scores through `conmin_slice_scorer` (read-only per the guardrail, so
   it would need a caller of its own) or a small ConGen-side scorer. Not resolved here because
   it depends on which CSV the baseline rows land in.
4. Exact library versions — pinned at implementation, recorded back into this plan.
5. Whether the ⅔ training split is what the baseline should use, or whether the learner should
   see all of `E⁺ ∪ E⁻` per fold. Must match whatever ConGen sees on the same fold; assumed ⅔
   here.
