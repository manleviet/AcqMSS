# Phase 02: Dict-Based Strategy Mapping

## Context Links

- [generate_examples.py](../../apps/generate_examples.py) (lines 70-110)

## Overview

- **Priority**: P2
- **Status**: completed
- **Effort**: 20m

Replace 9-branch `if/elif` chain in `get_example_count_for_strategy()` with a dictionary lookup. Current function is 40 lines; dict approach ~15 lines.

## Key Insights

- Most strategies are simple multipliers: `rs_1n` = 1*n, `rs_2n` = 2*n, `rs_3n` = 3*n
- `rs_m` returns `m_value` (pre-computed), `2cov` returns None, `ff` = 10*n, `balanced` = 2*n
- All branches follow pattern: return `multiplier * n_features` or special value

## Requirements

- Same return values for every input combination
- Same `ValueError` for unknown strategies
- Keep docstring explaining paper strategies

## Architecture

```python
# Strategy -> (multiplier_or_callable)
STRATEGY_COUNTS = {
    'rs_1n': lambda n, m: n,
    'rs_2n': lambda n, m: 2 * n,
    'rs_3n': lambda n, m: 3 * n,
    'rs_m': lambda n, m: m,
    '2cov': lambda n, m: None,
    'ff': lambda n, m: 10 * n,
    'balanced': lambda n, m: 2 * n,
}
```

## Related Code Files

- **Modify**: `apps/generate_examples.py` -- replace `get_example_count_for_strategy()` function

## Implementation Steps

1. Define `STRATEGY_COUNTS` dict at module level (after imports, before functions)
2. Replace `get_example_count_for_strategy()` body with dict lookup + ValueError fallback
3. Preserve function signature and docstring
4. Verify: `PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml -v`

## Todo List

- [x] Add `STRATEGY_COUNTS` module-level dict
- [x] Rewrite `get_example_count_for_strategy()` as dict lookup
- [x] Run verification command

## Success Criteria

- Function returns identical values for all strategy/n/m combinations
- Unknown strategies still raise `ValueError`
- ~15 lines saved

## Risk Assessment

- **Very low risk**: Pure refactor of deterministic mapping
- Lambda approach keeps it readable; alternative is tuple of (multiplier, special_field) but lambdas are clearer here

## Next Steps

Proceed to Phase 03
