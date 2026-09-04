## Context

- Parent: [plan.md](plan.md)
- Docs: `docs/system-architecture.md`, `docs/code-standards.md`

## Overview

- **Priority**: P3
- **Status**: Complete
- **Description**: Move assumption ID → clauses/names resolution from ConGenRunner into ConGenModel

## Key Insights

- `ConGenRunner` lines 241-255 access `model.constraint_map` and `model.description_provider` directly — Feature Envy smell
- `ConGenResult.bg_clauses` is populated as `[[lit] for lit in set_bg]` in `ConGen.acquire()` — redundant since ConGenModel can resolve via `constraint_map`
- Line 138 has `# TODO: check lại` — confirms this was a known concern
- `ConGenRunResult.bg_clauses` must stay (used by cross_validation, kb_comparator, result_loader)

## Related Code Files

### Modify
- `conacq/algorithms/acqmss/congen_model.py` — Add methods
- `conacq/algorithms/acqmss/congen.py` — Remove `bg_clauses` from `ConGenResult` + `acquire()`
- `conacq/runners/congen_runner.py` — Simplify resolution block
- `tests/test_congen.py` — Remove `result.bg_clauses` assertions

### No changes needed
- `conacq/runners/congen_runner.py` `ConGenRunResult` — keeps `bg_clauses` field (populated from `resolve_result()`)
- `conacq/eval/result_loader.py` `ConGenResultData` — separate class, unaffected
- `conacq/eval/cross_validation.py` — uses `run_result.bg_clauses` (ConGenRunResult), not ConGenResult
- `conacq/eval/kb_comparator.py` — uses `ConGenResultData.bg_clauses`, not ConGenResult
- `apps/run_congen.py` — uses `ConGenRunResult.bg_clauses`, not ConGenResult

## Implementation Steps

### Step 1: Add methods to ConGenModel

In `conacq/algorithms/acqmss/congen_model.py`:

1. Add import: `from conacq.algorithms.acqmss.congen import ConGenResult`
2. Add `_resolve_ids(self, assumption_ids: List[int]) -> Tuple[List[List[int]], List[str]]`:
   - Iterate assumption_ids
   - For each: `description_provider.get_description(aid)` → name
   - If name in `constraint_map` → extend clauses
   - Return `(clauses, names)`
3. Add `resolve_result(self, result: ConGenResult) -> Tuple[List[List[int]], List[List[int]], List[str], List[str]]`:
   - `bg_clauses, _ = self._resolve_ids(self.get_b())`
   - `kb_clauses, kb_names = self._resolve_ids(result.kb_assumption_ids)`
   - `_, redundant_names = self._resolve_ids(result.redundant_ids)`
   - Return `(bg_clauses, kb_clauses, kb_names, redundant_names)`

### Step 2: Remove bg_clauses from ConGenResult

In `conacq/algorithms/acqmss/congen.py`:

1. Remove field `bg_clauses: List[List[int]] = field(default_factory=list)` from `ConGenResult`
2. In `acquire()` early return (line 105-112): remove `bg_clauses` construction + kwarg
3. In `acquire()` normal return (line 138-146): remove `bg_clauses` construction + kwarg

### Step 3: Update ConGenRunner

In `conacq/runners/congen_runner.py`:

Replace lines 241-255:
```python
# OLD
bg_clauses = self.oracle.get_root_clauses()
provider = self.model.description_provider
kb_clauses = []
kb_names = []
redundant_names = []
for aid in result.kb_assumption_ids:
    ...
for aid in result.redundant_ids:
    ...
```

With:
```python
# NEW
bg_clauses, kb_clauses, kb_names, redundant_names = \
    self.model.resolve_result(result)
```

### Step 4: Update tests

In `tests/test_congen.py`, remove 3 assertions:
- Line 108-109: `assert len(result.bg_clauses) > 0`
- Line 155-156: `assert len(result.bg_clauses) > 0`
- Line 201-202: `assert len(result.bg_clauses) > 0`

## Todo List

- [x] Add `_resolve_ids()` and `resolve_result()` to ConGenModel
- [x] Remove `bg_clauses` from ConGenResult dataclass
- [x] Remove `bg_clauses` construction in ConGen.acquire() (2 places)
- [x] Replace Runner resolution block with `model.resolve_result(result)`
- [x] Remove `result.bg_clauses` assertions in test_congen.py
- [x] Run full test suite

## Success Criteria

- All tests pass
- ConGenRunner no longer accesses `model.constraint_map` or `model.description_provider` for result resolution
- `ConGenResult` no longer has `bg_clauses` field
- `ConGenRunResult.bg_clauses` still populated correctly

## Risk Assessment

- **Low risk**: Pure extract-method refactoring, no behavior change
- **Circular import**: `ConGenModel` importing `ConGenResult` — both in same package, OK
- **BG clauses equivalence**: `_resolve_ids(self.get_b())` via constraint_map must produce same clauses as old `oracle.get_root_clauses()` — verify in tests
