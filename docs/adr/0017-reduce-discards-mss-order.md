# ADR-0017: REDUCE discards the MSS ordering through `set()` — restoring it changes which redundant constraint survives, and the golden tables

**Status:** Accepted — decision made; implementation + AcqMSS/ConGen golden regeneration deferred to a separate, gated command (run separately from ADR-0016)
**Date:** 2026-07-19
**Deciders:** Viet-Man Le
**Relates to:** ADR-0016 (the sibling `set()`-drops-order defect in QuAcq), ADR-0001 (behaviour held identical to `main`)

## Context

`conacq/algorithms/acqmss/reduce.py:63`, forming the KB that REDUCE minimizes:

```python
# KB ← B' ∪ NE
kb = list(set(set_b_prime) | set(set_neg_tv))
```

AcqMSS produces its KB as an ordered `gamma1 + gamma2` (`set_b_prime` then `set_neg_tv`). Wrapping both in `set()` and unioning **discards that order**; `kb` is then iterated (`for c in kb:`) in hash order. When two constraints are **mutually redundant**, REDUCE keeps whichever it reaches first — so *which representative survives* depends on the discarded order. That can move `n_kb`, `kb_reduction_ratio`, and the TP/FP split.

As with ADR-0016, the golden tables are green today only because integer-set iteration is deterministic per build — a stable substitute for the intended order, not the intended order itself.

## Why this is blocked (not a Group-A refactor)

The fix — preserve `gamma1 + gamma2` order while de-duplicating — changes which mutually-redundant constraint is removed → changes the reduced KB → changes `n_kb` / `kb_reduction_ratio` / TP / FP → **changes the AcqMSS golden tables**. It is a behaviour change by construction; there is no behaviour-inert form.

## Decision (proposed)

Record the defect and **gate the fix behind a golden regeneration.** Do not rewrite line 63 as a cleanup.

When approved, the fix preserves order with a first-occurrence dedup, e.g.:

```python
# KB ← B' ∪ NE, preserving AcqMSS's gamma1+gamma2 order
kb = list(dict.fromkeys(list(set_b_prime) + list(set_neg_tv)))
```

(`dict.fromkeys` keeps first occurrence and insertion order; the two `set()`s only ever provided membership dedup, which this preserves.)

## Options considered

### Option A — preserve `gamma1 + gamma2` order — **CHOSEN**
Makes the surviving-representative choice deterministic *and* faithful to the algorithm's stated ordering. Requires regenerating the AcqMSS golden tables and re-validating the paper's AcqMSS numbers.

### Option B — status quo
Rejected as a silent trap: the current numbers depend on Python's hash-iteration order of ints, which is stable per build but is not the algorithm's defined semantics; a future reader "tidying" the `set()` would move the golden numbers unknowingly.

## Sequencing: run separately from ADR-0016

Although ADR-0016 and ADR-0017 are both "`set()` drops order" in the same conacq layer, they are implemented and regenerated **as two separate, gated commits — B2 (0016) first, then B3 (0017)** — so each golden diff maps to exactly one code change and is reviewable in isolation.

## Implementation contract (deferred — executes on a separate, gated command, after ADR-0016)

The fix at `reduce.py:63` preserves the `gamma1 + gamma2` appearance order while de-duplicating (`dict.fromkeys(list(set_b_prime) + list(set_neg_tv))`, or an equivalent seen-set), never routing through `set()`. When the gated command runs, it MUST satisfy:

1. **Prove the reorder now bites.** Add/point to a test showing the surviving redundant representative follows `gamma1+gamma2` order deterministically, distinguishable from the old hash-order outcome (if it can't be distinguished, the fix has not taken).
2. **Regenerate golden, itemized.** List exactly which golden file(s) changed and how many `n_kb` / `kb_reduction_ratio` / TP / FP cells moved; for each, show the move is caused by the reorder, not a new bug — a review artifact for Cowork *before* commit.
3. **No collateral regression.** The rest of the suite (outside the regenerated AcqMSS/ConGen golden) stays green.
4. **Close the loop.** Record here which golden was regenerated, and add a paper-regen note that the AcqMSS/ConGen numbers changed vs the old draft.

## What must be regenerated

- **Golden:** AcqMSS / ConGen golden tables — `n_kb`, `kb_reduction_ratio`, and TP/FP-derived metrics.
- **Paper:** the AcqMSS results tables that report KB size / reduction ratio / precision-recall.
- QuAcq-only tables are unaffected (ADR-0016 handles those separately).
