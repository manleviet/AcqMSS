# ADR-0015: The example-mode pool shuffle must be seeded — its current OS-entropy shuffle makes one paper table irreproducible

**Status:** Accepted — decision made; implementation + table regeneration deferred to paper-writing
**Date:** 2026-07-19
**Deciders:** Viet-Man Le
**Relates to:** the T16 RNG-isolation work (per-generator `random.Random` instances), ADR-0001 (behaviour held identical to `main` — this is the one place that identity is *not* a virtue)

## Context

`conacq/example_generators/query_provider.py:60` shuffles the example pool:

```python
if pool is not None:
    self._pool = list(pool)
    random.Random(seed).shuffle(self._pool)
```

The T16 RNG-isolation pass moved this off the process-global `random` stream and onto a per-call `random.Random(seed)` instance — a real improvement (one generator no longer perturbs another). But `seed` still defaults to `None`, and `random.Random(None)` seeds from OS entropy. So in **example mode** the pool is shuffled **differently on every run**, and the order in which pooled examples are consumed is not reproducible.

**One paper table is produced in example mode.** Because its example order came from an unseeded shuffle, that table **cannot be reproduced — not even by the author.** Re-running the pipeline today yields a (statistically similar but) numerically different table.

This is *not* current test flakiness: the golden/characterization suite passes seed-fixed inputs, so the determinism defect is invisible to CI. It is a **reproducibility** defect that only bites the published example-mode numbers.

## Why this is blocked (not a Group-A refactor)

A behaviour-inert fix is impossible here **by definition**: the whole point is to make the shuffle *deterministic*, which changes the example draw order → changes the learned KB → changes the example-mode table. Fixing it **changes frozen output**. It therefore cannot ride in the behaviour-inert batch; it needs a regeneration decision and a paper update.

## Decision

1. **Do not** apply the naive "if `seed is None`, skip the shuffle" fix. Example mode *must* randomize the pool — dropping the shuffle silently kills the randomization the experiment depends on.
2. **Always pass a fixed, recorded, deterministic per-fold seed** for the example-mode pool (Option B below), decoupled from the `shuffle_bias` knob, matching how ConGen already seeds per fold.
3. Regenerate the affected example-mode table with that seed and update the number in the paper.

**Implementation + table regen are deferred to paper-writing time** (the numbers are not being consumed before then), but the seed strategy is decided now so the future regen is a mechanical step, not a re-decision.

## Options considered (seed strategy)

### Option A — a single constant seed for every example-mode pool
Simplest and fully reproducible. All folds share one pool order. Not chosen: loses per-fold independence.

### Option B — a deterministic per-fold seed (e.g. `base_seed + fold_index`), matching ConGen — **CHOSEN**
Preserves fold-to-fold variation while staying reproducible, and is consistent with how the rest of the evaluation already seeds.

### Option C — leave `seed=None` (status quo)
Rejected: the published example-mode table stays irreproducible.

## What must be regenerated (the freeze this touches)

- **Paper:** the one example-mode results table (identify it against the paper's table inventory before regen).
- **Golden / `data/results/**`:** any example-mode cross-validation outputs that feed that table, if they are pinned. Bias-/oracle-mode tables are **not** affected — this is scoped strictly to the example-mode path.

## Consequences

- Once seeded, the example-mode table becomes reproducible on demand (the seed is recorded).
- One-time cost: a regen run + a single number update in the paper. Not a one-liner — it is a data/paper migration gated on this ADR.

## Resolved / carried to implementation time

- **Seed strategy:** per-fold (Option B) — decided.
- **Deferred to paper-writing:** the actual code change + regenerating the one example-mode table (and, if pinned, its `data/results/**` source), plus identifying that table against the paper's table inventory. Tracked here; not blocking the current behaviour-inert branch.
