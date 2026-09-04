# Fix Assumption ID / Bias ID Mismatch in Test Print Logic

## Problem

Two separate ID systems exist:
- **Bias constraint IDs** (`str`): `"c1"`, `"c2"` — stored in `Constraint.id`
- **Assumption IDs** (`int`): `1003`, `1005` — SAT solver literals from `prepare_kb()`

`Bias.get_constraint_by_id(cid: str)` expects **string** IDs.
Tests pass **integer** assumption IDs from `ConGenResult.kb_assumption_ids` → always returns `None`.

## Scope

**Affected: 3 locations in `test_congen.py`** (display-only bug, silent failure):
- Line 115-119: `test_congen_incremental_with_rs_examples`
- Line 162-166: `test_congen_non_incremental_with_rs_examples`
- Line 207-211: `test_congen_incremental_with_ff_examples`

**NOT affected** (already correct):
- `test_interactive.py:278-282` — `InteractiveResult.kb_constraints` is `List[str]` (constraint IDs like `"c1"`) ✅
- `congen_runner.py:207-211` — Uses `provider.get_description(aid)` to bridge int→str ✅
- `run_congen_eval.py:190` — Uses `ConGenRunResult.kb_constraints` which is `List[str]` ✅
- `interactive_runner.py:178` — Uses string constraint IDs from `InteractiveResult` ✅

## Fix Strategy

Bridge via `DescriptionProvider`: `int assumption_id → str constraint_name → Constraint`.

The `ConGenModel.description_provider` is already available after `prepare()`. The `create_checker_and_task()` helper already holds the model. Need to expose it to test methods.

## Phase 1: Fix test_congen.py

| Status | Step |
|--------|------|
| [ ] | Modify `create_checker_and_task()` to also return `model` (or `model.description_provider`) |
| [ ] | Update 3 test methods to use `provider.get_description(c)` to bridge int→str before calling `bias.get_constraint_by_id()` |
| [ ] | Run tests to verify output is no longer `None` |

### Code Change

**Before:**
```python
for c in result.kb_assumption_ids:
    constraint = bias.get_constraint_by_id(c)  # int vs str → None
    print(f"  Constraint: {constraint} (ID: {c})")
```

**After:**
```python
for c in result.kb_assumption_ids:
    cname = provider.get_description(c)  # int → str
    constraint = bias.get_constraint_by_id(cname)  # str → Constraint
    print(f"  Constraint: {constraint} (ID: {c})")
```

## Risk Assessment

- **Impact**: Display-only — no functional/assertion impact
- **Risk**: Very low — only changes print output in test methods
- **Backward compatibility**: No API changes
