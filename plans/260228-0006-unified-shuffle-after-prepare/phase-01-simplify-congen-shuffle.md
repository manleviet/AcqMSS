# Phase 1: Simplify ConGenRunner Shuffle

## Context
- Parent: [plan.md](plan.md)
- File: `conacq/runners/congen_runner.py`

## Overview
- Priority: P3
- Description: Remove constraint_map shuffle, replace with set_c shuffle after prepare()
- Implementation status: complete
- Review status: complete

## Key Insights
- SAT solver doesn't care about clause order — only set_c iteration order matters
- prepare() creates fresh ConGenTask each call → set_c is always fresh
- Shuffling set_c after prepare() = shuffling constraint_map before prepare()

## Requirements
- Remove `_original_bias_constraint_order` snapshot from `__init__`
- Remove constraint_map shuffle block from `run()`
- Add set_c shuffle after prepare() in `run()`
- Preserve deterministic behavior (same seed → same result)

## Related Code Files
- Modify: `conacq/runners/congen_runner.py`
- Test: `tests/test_congen.py`

## Implementation Steps

1. In `__init__` (line 120): Delete `self._original_bias_constraint_order = list(self.model.constraint_map.keys())`

2. In `run()` (lines 157-161): Delete entire shuffle block:
   ```python
   # DELETE:
   if shuffle_seed is not None:
       keys = list(self._original_bias_constraint_order)
       random.Random(shuffle_seed).shuffle(keys)
       self.model.constraint_map = {k: self.model.constraint_map[k] for k in keys}
       logging.debug('Shuffled bias with seed=%d', shuffle_seed)
   ```

3. In `run()`, after `task = self.model.task` (line 168): Add shuffle:
   ```python
   # Shuffle bias iteration order if seed provided
   if shuffle_seed is not None:
       random.Random(shuffle_seed).shuffle(task.set_c)
       logging.debug('Shuffled set_c with seed=%d', shuffle_seed)
   ```

## Todo List
- [ ] Remove _original_bias_constraint_order from __init__
- [ ] Remove constraint_map shuffle block from run()
- [ ] Add set_c shuffle after prepare() in run()
- [ ] Update docstring if needed

## Success Criteria
- ConGenRunner no longer has _original_bias_constraint_order field
- Shuffle happens on task.set_c after prepare()
- All ConGen tests pass

## Risk Assessment
- Low risk: mathematically equivalent transformation
- Mitigation: full test suite validates correctness
