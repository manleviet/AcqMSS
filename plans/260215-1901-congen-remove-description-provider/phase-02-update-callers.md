# Phase 2: Update Callers

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-simplify-congen-and-result.md)

## Overview
- **Priority:** High
- **Status:** complete
- **Description:** Update all 4 caller sites to use new CONGENResult API (raw IDs) and resolve names externally.

## Key Insights
- `congen_runner.py:200` has fragile pattern: uses `result.kb_constraints` (description strings) as keys into `constraint_map` (Dict[str, ...]). Must fix to use proper ID-based lookup.
- **Bridge discovered:** `DescriptionProvider.get_description(assumption_id)` returns the constraint name string — the same string used as keys in `ConGenModel.constraint_map`. So the mapping chain is: `assumption_id (int) → provider.get_description() → constraint_name (str) → constraint_map[name]`.
- Tests print names via `bias.get_constraint_by_id(c)` — they already handle name resolution themselves, just need to switch from `kb_constraints` to `kb_assumption_ids`.

## Requirements
- All callers remove `description_provider=` kwarg from acquire() calls
- Name resolution happens at caller boundary (display/output only)
- congen_runner.py uses ID-based lookups for kb_clauses

## Related Code Files
- **Modify:** `apps/run_congen.py` (line 125-142)
- **Modify:** `acqmss/eval/congen_runner.py` (line 172-214)
- **Modify:** `tests/test_congen.py` (lines 85-112, 130-158, 176-203)

## Implementation Steps

### A. `apps/run_congen.py` (line 125-142)
1. Remove `description_provider=congen_model.description_provider` from acquire() call (line 131)
2. For verbose output (lines 137-142): use `resolve_congen_names()` or `congen_model.description_provider` directly to resolve names for display
3. For save_result (line 147): pass `description_provider` to save_result() if names needed in JSON

### B. `acqmss/eval/congen_runner.py` (line 172-214)
1. Remove `description_provider=self.model.description_provider` from acquire() call (line 178)
2. **Fix kb_clauses lookup** (lines 199-202) using the bridge pattern:
   ```python
   # Before (fragile — description strings as lookup keys):
   for cid in result.kb_constraints:
       if cid in self.model.constraint_map:
           kb_clauses.extend(self.model.constraint_map[cid])

   # After (explicit — assumption_id → name → clauses):
   provider = self.model.description_provider
   for aid in result.kb_assumption_ids:
       cname = provider.get_description(aid)
       if cname in self.model.constraint_map:
           kb_clauses.extend(self.model.constraint_map[cname])
   ```
3. Update ConGenRunResult construction (lines 204-213): resolve names via provider for `kb_constraints` and `redundant_constraints` fields
4. **Consider** whether ConGenRunResult also needs simplification (kb_constraints/redundant_constraints fields → IDs)

### C. `tests/test_congen.py` (3 test methods)
1. Remove `description_provider=congen_model.description_provider` from all 3 acquire() calls (lines 91, 136, 182)
2. Update assertions: `result.kb_constraints` -> `result.kb_assumption_ids`
3. Print statements already use `bias.get_constraint_by_id(c)` — just change iteration from `result.kb_constraints` to `result.kb_assumption_ids`

## Todo
- [x] Update apps/run_congen.py — remove provider, add external name resolution for display
- [x] Update acqmss/eval/congen_runner.py — remove provider, fix kb_clauses lookup
- [x] Update tests/test_congen.py — remove provider, switch to kb_assumption_ids
- [x] Verify ConGenRunResult in congen_runner.py aligns with new CONGENResult fields

## Success Criteria
- No caller passes description_provider to acquire()
- congen_runner.py uses ID-based lookup (not string-based)
- All callers compile without errors
- Name resolution only happens at display/output boundaries

## Risk Assessment
- **Low (mitigated):** congen_runner.py kb_clauses lookup solved via `DescriptionProvider.get_description(assumption_id)` → returns constraint name string that matches `constraint_map` keys. No new mapping needed — the existing provider is the bridge.

## Security Considerations
- None

## Next Steps
- Phase 3: Run tests to verify
