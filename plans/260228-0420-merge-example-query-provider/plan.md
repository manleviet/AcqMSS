---
title: "Merge ExampleProvider + QueryGenerator into QueryProvider"
description: "Unify two query sources into single QueryProvider with pool-filtered + SAT strategies"
status: completed
priority: P2
effort: 3h
branch: main
tags: [refactoring, quacq, DRY, KISS]
created: 2026-02-28
completed: 2026-02-28
---

# Merge ExampleProvider + QueryGenerator into QueryProvider

## Problem

ExampleProvider returns examples blindly (no paper conditions). QueryGenerator uses SAT. Both serve same purpose: provide next query. Two classes + mode dispatch in QuAcq.learn() adds complexity.

## Solution

Single `QueryProvider` class with three methods matching paper modes:
- `generate_from_pool()` -- paper-filtered pool (satisfies C_L + BG, violates >=1 bias)
- `generate_from_sat()` -- current QueryGenerator.generate() logic
- `generate()` -- pool first, SAT fallback

Remove `_narrow_with_pool` from FindC (paper Algorithm 3 does NOT use pool). Keep DiscriminatingGenerator separate.

## Phases

| # | Phase | Status | Est |
|---|-------|--------|-----|
| 1 | [Create QueryProvider class](phase-01-create-query-provider.md) | completed | 45m |
| 2 | [Update QuAcq algorithm](phase-02-update-quacq.md) | completed | 30m |
| 3 | [Simplify FindC](phase-03-simplify-findc.md) | completed | 20m |
| 4 | [Update runner and consumers](phase-04-update-runner-consumers.md) | completed | 20m |
| 5 | [Delete ExampleProvider + update tests](phase-05-delete-update-tests.md) | completed | 30m |
| 6 | [Update documentation](phase-06-update-docs.md) | completed | 15m |

## Key Decisions

1. Pool filter: full paper condition with SAT check (satisfies C_L + BG AND violates >=1 c in B)
2. Mode mapping: oracle -> SAT, example_only -> pool, example_first -> pool+SAT
3. DiscriminatingGenerator stays separate (different condition: separate c_i from c_j)
4. `_narrow_with_pool` removed from FindC (paper Algorithm 3 uses only DiscriminatingGenerator)

## Dependencies

- Brainstorm: `plans/reports/brainstorm-260228-0420-merge-example-query-provider.md`

## Success Criteria

- [ ] QueryProvider replaces both ExampleProvider and QueryGenerator
- [ ] Pool examples filtered by paper's condition
- [ ] FindC uses DiscriminatingGenerator only (no pool)
- [ ] All three modes work correctly
- [ ] All existing tests pass (updated for new API)
