# Phase 3: Update Tests & Documentation

## Context Links

- [Impact Analysis](reports/impact-analysis.md)
- [Phase 2](phase-02-update-generate-ne-consumers.md) (prerequisite)

## Overview

- **Priority**: Medium (tests must pass; docs must be accurate)
- **Status**: complete
- **Description**: Update test files referencing `set_ne` and all documentation files.

## Key Insights

- `test_congen.py` has 3 call sites using `set_ne=task.set_ne`
- CLAUDE.md, code-standards.md, system-architecture.md all reference `set_ne`
- `__init__.py` exports are unaffected (no `set_ne` export)

## Requirements

### Functional
- All tests pass after rename
- All docs accurately reflect `set_neg_tv` instead of `set_ne`

### Non-Functional
- Docstring examples match actual API

## Related Code Files

### Modify
- `tests/test_congen.py` — 3 caller sites (lines 90, 134, 179)
- `CLAUDE.md` — API example (line 189)
- `docs/code-standards.md` — API example (lines 261, 270, 293)
- `docs/system-architecture.md` — architecture docs (lines 75, 91, 220, 327, 333)
- `docs/codebase-summary.md` — if any `set_ne` references

## Implementation Steps

### Step 1: Update test_congen.py

3 identical changes at lines 90, 134, 179:
```python
# Before
set_ne=task.set_ne,
# After
set_neg_tv=task.set_neg_tv,
```

### Step 2: Update CLAUDE.md

Line 189:
```python
# Before
set_ne=model.task.set_ne,  # NE assumption IDs (from prepare())
# After
set_neg_tv=model.task.set_neg_tv,  # NE assumption IDs (from prepare())
```

Also update the `ConGenTask` description and any API example showing `set_ne`.

### Step 3: Update docs/code-standards.md

Lines 261, 270, 293 — update code examples:
```python
# Before
set_ne: List[int],  # NE assumption IDs
mss = self._acqmss(set_b, set_ne, set_tc, set_bg)
set_ne=model.task.set_ne,
# After
set_neg_tv: List[int],  # NE assumption IDs
mss = self._acqmss(set_b, set_neg_tv, set_tc, set_bg)
set_neg_tv=model.task.set_neg_tv,
```

### Step 4: Update docs/system-architecture.md

Lines 75, 91, 220, 327, 333 — update all `set_ne` references:
- Line 75: `set_ne=model.task.set_ne` -> `set_neg_tv=model.task.set_neg_tv`
- Line 91: `NE (set_ne)` -> `NE (set_neg_tv)`
- Line 220: `set_ne: list[int]` -> remove (inherits from TestCaseTask)
- Line 327: `merge_ne_into_task() -> set_ne populated` -> `set_neg_tv populated`
- Line 333: `acquire(set_b, set_bg, set_tc, set_ne, ...)` -> `set_neg_tv`

### Step 5: Update docs/codebase-summary.md

Search and replace any remaining `set_ne` references.

## Todo List

- [ ] Update test_congen.py line 90: `set_ne=task.set_ne` -> `set_neg_tv=task.set_neg_tv`
- [ ] Update test_congen.py line 134: same change
- [ ] Update test_congen.py line 179: same change
- [ ] Update CLAUDE.md API example
- [ ] Update docs/code-standards.md (3 locations)
- [ ] Update docs/system-architecture.md (5 locations)
- [ ] Update docs/codebase-summary.md if needed
- [ ] Run `PYTHONPATH=. pytest tests/test_congen.py -v` — all tests pass
- [ ] Run `grep -r "set_ne" acqmss/ apps/ tests/ docs/ CLAUDE.md` — zero matches

## Success Criteria

- `PYTHONPATH=. pytest tests/ -v` passes
- No remaining `set_ne` references in source code or docs (except plan files)
- Documentation examples match actual API signatures

## Risk Assessment

- **Low**: Mechanical search-and-replace
- **Verification**: Final grep confirms completeness

## Security Considerations

- None

## Next Steps

- Run full test suite to verify
- Commit with message: `refactor(task): remove redundant set_ne, reuse set_neg_tv from TestCaseTask`
