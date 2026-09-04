# Phase 4: Narrow `_apply_reduce` Exception Handling

## Context
- Parent: [plan.md](plan.md)
- Independent
- Review: Issue #3

## Overview
- **Priority**: High
- **Status**: complete
- **Description**: Replace broad `except Exception` with specific exceptions in `_apply_reduce`. Log traceback for debugging.

## Related Code Files

- **Modify**: `conacq/algorithms/interactive/quacq.py` (lines 319-321)

## Implementation Steps

### 1. Replace broad exception (quacq.py lines 319-321)

Replace:
```python
except Exception as e:
    logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
    return list(task.learned_kb)
```

With:
```python
except (RuntimeError, KeyError, ValueError) as e:
    logging.warning('REDUCE failed: %s, returning learned KB as-is', e, exc_info=True)
    return list(task.learned_kb)
```

- `RuntimeError`: checker/solver failures
- `KeyError`: missing negation_map entries
- `ValueError`: invalid assumption IDs
- `exc_info=True`: logs full traceback at WARNING level

## Todo

- [x] Narrow exception types
- [x] Add `exc_info=True` for traceback logging

## Success Criteria

- Only expected REDUCE failures caught
- Unexpected errors propagate (e.g., `TypeError`, `AttributeError`)
- Traceback visible in logs for debugging
