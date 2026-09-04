# Phase 1: Refactor GenerateNE & Extract Helpers from prepare()

## Context

- Parent plan: [plan.md](plan.md)
- Primary files: `acqmss/algorithms/task_preparation.py`, `acqmss/algorithms/generate_ne.py`
- Method: `ConGenTaskPreparation.prepare()` (lines 137-330)

## Overview

- **Priority**: High
- **Status**: pending
- **Description**: Modify `GenerateNE.generate()` to match inline behavior in `prepare()`, then delegate Step 3 to it. Extract combine/negate logic into helpers.

## Key Insights

- Step 3 occupies ~130 of 190 lines — primary extraction target
- `GenerateNE.generate()` exists but differs from inline code in 3 ways:
  1. **Assignment mapping**: inline creates per-assignment clauses on-the-fly; `GenerateNE` uses pre-mapped `_pos/_neg_assignment_to_assumption`
  2. **Combining**: inline handles conjunction of multiple NEs + negated forms; `GenerateNE` returns raw clauses only
  3. **KB merging**: inline merges `oracle.get_kb() + result.set_kb`; `GenerateNE` uses its own checker
- NE combine logic (`if len(neg_tv) > 1`) appears twice (NE + negated NE) — DRY violation
- `_assign_sets()` only handles Steps 0-2; Step 3 populates `set_neg_tv` directly — correct behavior, no change needed

## Requirements

- Preserve **exact SAT encoding** (same assumption IDs, same clause structure)
- Reuse `GenerateNE.generate()` — modify it to match inline behavior
- Keep `prepare()` as orchestrator (~40 lines)
- Combine/negate logic as helpers on `ConGenTaskPreparation`

## Architecture

```
prepare()                                # orchestrator (~40 lines)
├── _prepare_bg()                        # existing (Step 0)
├── prepare_kb()                         # existing (Step 1)
├── prepare_testsuite_with_negation()    # existing (Step 2)
├── _assign_sets()                       # existing
└── _prepare_negative_examples()         # NEW (Step 3 orchestrator)
    ├── GenerateNE.generate()            # MODIFIED: match inline behavior
    ├── _combine_ne_constraints()        # NEW: combine NEs into single assumption
    └── _create_negated_ne()             # NEW: negated form of combined NE
```

## Related Code Files

- `acqmss/algorithms/task_preparation.py` — prepare() refactoring
- `acqmss/algorithms/generate_ne.py` — GenerateNE modification
- `explanation/operations/algorithms/checker.py` — NonIncrementalPySATChecker

## Gap Analysis: GenerateNE.generate() vs Inline Code

### Current GenerateNE.generate() behavior:
```python
# Uses pre-mapped assumptions (set at init)
assumption = self._pos_assignment_to_assumption[feat]
# Returns NEResult(new_clauses, set_neg_tv, next_tseitin_var)
# Does NOT combine or negate
```

### Inline code in prepare() Step 3:
```python
# Creates per-assignment clauses on-the-fly with id_assumption
clause = [var, -1 * id_assumption]
# Merges oracle.get_kb() + result.set_kb
# Runs QuickXPlain per testcase
# Combines multiple NEs into conjunction
# Creates negated form for REDUCE
```

### What needs to change in GenerateNE.generate():
1. Accept `model` (or oracle + result KB) to build merged KB per testcase
2. Create per-assignment clauses on-the-fly (not pre-mapped)
3. Return per-testcase NE results (literals + descriptions) for caller to combine

## Implementation Steps

### Step 1: Modify GenerateNE.generate() signature & behavior

Adjust `generate()` to:
- Accept `model` variables, oracle, result KB/assumptions (instead of pre-mapped assignments)
- Per testcase: merge KBs, create assignment clauses with `id_assumption`, run QuickXPlain
- Return per-testcase results: `List[NEPerTestcase]` where each has `(ne_clause, ne_id, desc)`

```python
@dataclass
class NEPerTestcase:
    ne_id: int           # assumption ID for this NE
    ne_clause: List[int] # blocking clause with assumption literal
    desc: str            # description for provider
```

### Step 2: Extract `_combine_ne_constraints()` on ConGenTaskPreparation

- Input: `result, provider, ne_results: List[NEPerTestcase], id_assumption`
- If single NE → add directly to assumptions + set_neg_tv
- If multiple NEs → create conjunction via implication clauses
- Return: `(ne_id: int, id_assumption: int)`

### Step 3: Extract `_create_negated_ne()` on ConGenTaskPreparation

- Input: `result, provider, neg_tv_ids, ne_id, id_assumption`
- Create negated form: ¬(¬e1 ∧ ¬e2 ∧ ...) = disjunction
- Handle single vs multiple
- Return: `(negated_ne_id: int, id_assumption: int)`

### Step 4: Extract `_prepare_negative_examples()` orchestrator

- Input: `result, provider, model, testsuite, id_assumption`
- Create NonIncrementalPySATChecker (merged KB)
- Call `GenerateNE(checker, oracle).generate(...)` → get per-testcase results
- Add NE clauses to result.set_kb
- Call `_combine_ne_constraints()` then `_create_negated_ne()`
- Populate `result.set_neg_tv` and `result.neg_tc_map`
- Return: `id_assumption`

### Step 5: Simplify `prepare()`

Replace entire Step 3 block (~130 lines) with:
```python
if testsuite is not None and len(testsuite.testcases) > 0:
    id_assumption = self._prepare_negative_examples(
        result, provider, model, testsuite, id_assumption)
```

## Todo

- [ ] Define `NEPerTestcase` dataclass
- [ ] Modify `GenerateNE.generate()` to match inline behavior
- [ ] Extract `_combine_ne_constraints()`
- [ ] Extract `_create_negated_ne()`
- [ ] Extract `_prepare_negative_examples()` orchestrator
- [ ] Update `prepare()` to delegate Step 3
- [ ] Verify ID progression matches exactly

## Success Criteria

- `prepare()` body ≤ 50 lines
- `GenerateNE.generate()` handles per-testcase NE creation
- Combine + negate logic in focused helpers (≤ 40 lines each)
- All existing tests pass unchanged
- SAT encoding output identical (same IDs, same clauses)

## Risk Assessment

- **ID synchronization**: Must ensure `id_assumption` progression in modified `GenerateNE` matches inline code exactly. Mitigation: per-testcase tracking, return updated ID.
- **GenerateNE breaking change**: Other callers may depend on current `generate()` API. Mitigation: check all references before modifying signature.
- **Clause ordering**: SAT solver is order-independent, but test against exact output to be safe.
