# Phase 5: Tests

## Context
- Parent: [plan.md](plan.md)
- Depends on: All previous phases
- Review: Issues #1, recommended tests

## Overview
- **Priority**: High
- **Status**: complete
- **Description**: Add tests verifying BG clause handling for QuAcqTask. Verify existing tests pass.

## Related Code Files

- **Modify**: `tests/test_interactive.py`

## Implementation Steps

### 1. Test `background_clauses` field

Add to `TestQuAcqTask` class:
```python
def test_background_clauses_field(self):
    """QuAcqTask.background_clauses stores raw BG CNF clauses."""
    task = QuAcqTask(
        background=[5, 6],  # Assumption IDs
        background_clauses=[[1], [2, -3]],  # Raw clauses
    )
    self.assertEqual(task.background, [5, 6])
    self.assertEqual(task.background_clauses, [[1], [2, -3]])

def test_background_clauses_clone(self):
    """clone() copies background_clauses."""
    task = QuAcqTask(
        background_clauses=[[1], [2, -3]],
    )
    cloned = task.clone()
    self.assertEqual(cloned.background_clauses, [[1], [2, -3]])
    cloned.background_clauses[0].append(99)
    self.assertNotEqual(task.background_clauses[0], cloned.background_clauses[0])
```

### 2. Test `get_bg_clauses` helper

Add test class for `_task_compat` helpers:
```python
class TestTaskCompat(unittest.TestCase):
    def test_get_bg_clauses_quacq_task(self):
        """get_bg_clauses returns background_clauses for QuAcqTask."""
        task = QuAcqTask(background_clauses=[[1], [2, -3]])
        from conacq.algorithms.interactive._task_compat import get_bg_clauses
        result = get_bg_clauses(task)
        self.assertEqual(result, [[1], [2, -3]])

    def test_get_bg_clauses_legacy_task(self):
        """get_bg_clauses wraps int IDs as unit clauses for InteractiveTask."""
        task = InteractiveTask(background=[1])
        from conacq.algorithms.interactive._task_compat import get_bg_clauses
        result = get_bg_clauses(task)
        self.assertEqual(result, [[1]])
```

### 3. Test InteractiveModel populates background_clauses

Add to `TestInteractiveModel` class:
```python
def test_prepare_populates_background_clauses(self):
    """InteractiveModel.prepare() populates background_clauses with raw BG clauses."""
    # Uses existing fm/bias test fixtures
    task = self.model.task
    self.assertIsInstance(task.background_clauses, list)
    self.assertTrue(len(task.background_clauses) > 0)
    # Each clause is a list of ints (no assumption guards)
    for clause in task.background_clauses:
        self.assertIsInstance(clause, list)
        for lit in clause:
            self.assertIsInstance(lit, int)
```

### 4. Run full test suite

```bash
PYTHONPATH=. pytest tests/ -v
```

Verify: 333+ passed, 0 new failures.

## Todo

- [x] Add `test_background_clauses_field`
- [x] Add `test_background_clauses_clone`
- [x] Add `TestTaskCompat` class
- [x] Add `test_prepare_populates_background_clauses`
- [x] Run full test suite — all pass

## Success Criteria

- New tests pass
- All existing tests pass (333+)
- BG clauses correctly populated and consumed
