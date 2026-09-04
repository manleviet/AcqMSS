# Phase 04: Simplify generate_examples_for_strategy

## Context Links

- [generate_examples.py](../../apps/generate_examples.py) (lines 113-169)

## Overview

- **Priority**: P2
- **Status**: completed
- **Effort**: 30m

`generate_examples_for_strategy()` (56 lines) is a dispatch function that selects a generator class, calls `.generate()` with strategy-specific args, then sets `metadata['strategy']`. Can be simplified with a factory dict + common metadata assignment.

## Key Insights

Current structure per branch:
1. Instantiate generator with oracle
2. Call `.generate()` with strategy-specific kwargs
3. Set `examples.metadata['strategy'] = strategy`
4. Optionally set extra metadata
5. Return

Problems:
- 4 nearly-identical branches
- Metadata assignment repeated in every branch
- `get_example_count_for_strategy()` called TWICE: once in `process_model()` (line 233, for display) and again in `generate_examples_for_strategy()` (line 135, for actual use) — DRY violation
- `calculate_distribution()` called at line 238 only for verbose display — compute once, reuse

**Decision**: For verbose display of n_pos/n_neg, use `examples.metadata['actual_positive']` and `examples.metadata['actual_negative']` AFTER generate() returns, instead of calling `calculate_distribution()` before generate(). Generators already store these values:
- `ControlledRandomSamplingGenerator` → `metadata['actual_positive']`, `metadata['actual_negative']`
- `BalancedRandomSamplingGenerator` → `metadata['actual_positive']`, `metadata['actual_negative']`
This eliminates the separate `calculate_distribution()` call entirely and shows ACTUAL counts (not estimates).

## Requirements

- Same generator selection per strategy
- Same `.generate()` arguments per strategy
- Same metadata on returned ExampleSet
- No behavior change

## Architecture

Replace 4 branches with a dispatch dict mapping strategy -> (GeneratorClass, generate_kwargs_builder):

```python
STRATEGY_GENERATORS = {
    'rs_1n': (ControlledRandomSamplingGenerator, lambda **kw: {'total': kw['n_examples'], 'valid_configs': kw['valid_configs'], 'seed': kw['seed']}),
    'rs_2n': ...,
    'rs_3n': ...,
    'rs_m': ...,
    '2cov': (TwoCoverageGenerator, lambda **kw: {'seed': kw['seed']}),
    'ff': (FeatureFrequencyGenerator, lambda **kw: {'max_examples': kw['n_examples'], 'seed': kw['seed']}),
    'balanced': (BalancedRandomSamplingGenerator, lambda **kw: {'n_positive': kw['n_features'], 'n_negative': kw['n_features'], 'seed': kw['seed']}),
}
```

**Alternative (simpler)**: Keep function but consolidate the 4 RS strategies into one branch since they all use `ControlledRandomSamplingGenerator` with same args. This reduces 4 branches to 3 groups:

```python
if strategy in ('rs_1n', 'rs_2n', 'rs_3n', 'rs_m'):
    ...
elif strategy == '2cov':
    ...
elif strategy == 'ff':
    ...
elif strategy == 'balanced':
    ...
```

This is already the current structure. The main savings come from:
1. Moving metadata assignment after the if/elif (DRY)
2. Removing per-branch `examples.metadata['strategy'] = strategy` (4 copies -> 1)

## Related Code Files

- **Modify**: `apps/generate_examples.py`

## Implementation Steps

1. Eliminate double `get_example_count_for_strategy()` call: compute `n_examples` once in `process_model()`, pass to `generate_examples_for_strategy()`
2. Remove `calculate_distribution()` call from `process_model()` verbose block (line 238); instead use `examples.metadata['actual_positive']` and `examples.metadata['actual_negative']` after generate returns
3. Factor out common metadata: move `metadata['strategy']` after if/elif block
4. Remove duplicate metadata lines from each branch (4→1)
5. Consider inlining into `process_model()` if function becomes trivially small
6. Verify: `PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml -v`

## Todo List

- [x] Compute `n_examples` once in `process_model()`, pass to `generate_examples_for_strategy()`
- [x] Remove `calculate_distribution()` call; use `examples.metadata` for verbose display
- [x] Move `metadata['strategy']` assignment after if/elif block
- [x] Remove duplicate metadata lines from each branch
- [x] Evaluate if function should be inlined into `process_model()`
- [x] Run verification command

## Success Criteria

- `metadata['strategy']` set exactly once after dispatch
- Fewer repeated lines in strategy branches
- ~10 lines saved
- Identical output

## Risk Assessment

- **Very low risk**: Only moving identical statements out of branches
- Inlining into `process_model()` is optional -- only do if it improves readability
- Keep extra metadata (`target_total`, `max_examples`) if they're used downstream; check before removing

## Security Considerations

N/A -- internal tool, no user input beyond config file

## Next Steps

After all 4 phases: run full verification, update `docs/codebase-summary.md` line counts
