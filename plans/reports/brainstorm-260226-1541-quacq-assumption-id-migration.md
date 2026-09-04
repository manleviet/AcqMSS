# Brainstorm: QuAcq Migration to Assumption IDs

**Date:** 2026-02-26
**Status:** Agreed
**Scope:** Full symmetric migration — QuAcq, FindScope, FindC, InteractiveTask, InteractiveResult

---

## Problem Statement

ConGen and QuAcq use different constraint representations:
- **ConGen**: assumption IDs (`int`) throughout — SAT-native, no conversion overhead
- **QuAcq**: string constraint IDs (`str`) throughout — requires temporary conversion for REDUCE

Goal: migrate QuAcq to assumption IDs for symmetry, enabling direct reuse of ConGen infrastructure (REDUCE, DescriptionProvider, checker pattern).

## User Decisions

| Decision       | Choice                                                    |
|----------------|-----------------------------------------------------------|
| Symmetry level | Parallel structure (separate QuAcqTask, same conventions) |
| REDUCE         | Direct call with assumption IDs (remove conversion layer) |
| Preparation    | Upfront — assign all assumption IDs before learning loop  |
| Output format  | Assumption IDs + DescriptionProvider for display          |
| Init pattern   | Model + prepare() (like ConGenModel)                      |
| Scope          | All at once — QuAcq + FindScope + FindC                   |

## Current Architecture (Before)

```
InteractiveLearner.from_files()
  → _build_task_from_bias() → InteractiveTask(bias=Set[str], constraint_map=Dict[str,clauses])
  → QuAcq.learn(task, oracle) → learning loop with string IDs
    → _prune_rejecting_constraints() — string iteration
    → _find_conflict() → FindScope + FindC — string operations
    → _reduce_kb() — builds temporary assumption IDs, calls REDUCE, maps back to strings
  → InteractiveResult(kb_constraints=List[str])
```

## Target Architecture (After)

```
InteractiveModel(bias, variables, constraint_map, negated_constraint_map)
  → .prepare(oracle) → InteractiveTaskPreparation
    → assign assumption IDs to all bias constraints (upfront)
    → create negation_map: Dict[int,int]
    → build set_kb with assumption guards
    → populate DescriptionProvider
  → QuAcqTask(bias=Set[int], set_kb, negation_map, assumptions, ...)
  → QuAcq.learn(task, oracle) → learning loop with assumption IDs
    → _prune_rejecting_constraints() — iterate assumption IDs
    → _find_conflict() → FindScope + FindC — assumption ID operations
    → REDUCE direct call (no conversion)
  → InteractiveResult(kb_assumption_ids=List[int])
  → DescriptionProvider.get_description(id) for display
```

## Approach: Evaluated Options

### Option A: Modify InteractiveTask in-place ❌
- Change all `str` fields to `int`
- Pro: No new classes
- Con: Breaks all tests, all callers, massive single commit. No rollback.

### Option B: Create parallel QuAcqTask + InteractiveModel ✅ (Chosen)
- New `QuAcqTask` dataclass parallel to `ConGenTask`
- New `InteractiveModel` parallel to `ConGenModel`
- New `InteractiveTaskPreparation` parallel to `ConGenTaskPreparation`
- Pro: Incremental, can coexist with old code during migration
- Con: Temporary duplication until old code removed

### Option C: Shared base with generics ❌
- Abstract base task with type parameter
- Over-engineered for 2 algorithms — YAGNI violation

## Detailed Design

### 1. QuAcqTask (new dataclass)

```python
@dataclass
class QuAcqTask:
    """Assumption-based task for QuAcq, parallel to ConGenTask."""
    bias: Set[int]                          # Bias constraint assumption IDs
    learned_kb: List[int]                   # Learned KB assumption IDs
    set_kb: List[List[int]]                # Full KB with assumption guards
    assumptions: List[int]                  # All assumption IDs
    negation_map: Dict[int, int]           # assumption → negated assumption
    background: List[int]                   # BG assumption IDs
    feature_ids: Dict[str, int]            # Feature name → SAT var
    id_to_feature: Dict[int, str]          # SAT var → feature name
    constraint_clauses: Dict[int, List[List[int]]]  # assumption_id → raw clauses (for violation checking)

    # Query stats (same as before)
    n_queries: int = 0
    query_history: List[Tuple[Dict[str, bool], bool]] = field(default_factory=list)
```

Key changes from InteractiveTask:
- `bias: Set[str]` → `Set[int]`
- `learned_kb: List[str]` → `List[int]`
- `constraint_map: Dict[str, clauses]` → `constraint_clauses: Dict[int, clauses]`
- Remove `negated_constraint_map` → use `negation_map: Dict[int,int]` (like ConGen)
- Add `set_kb`, `assumptions` (like ConGenTask)

### 2. InteractiveModel (new class)

```python
class InteractiveModel:
    """Model for interactive learning, parallel to ConGenModel."""
    def __init__(self, bias, variables, constraint_map, negated_constraint_map):
        # Store bias data (strings initially from BiasIO)
        ...

    def prepare(self, oracle: FeatureModelOracle) -> QuAcqTask:
        """Assign assumption IDs and build QuAcqTask."""
        # Similar to ConGenTaskPreparation but without E+/E-
        # Steps: BG from oracle → assign bias assumption IDs → negation_map → DescriptionProvider
        ...
```

### 3. InteractiveTaskPreparation (new class)

Reuses `prepare_kb()` helper from ConGen's task_preparation — the same function that assigns assumption IDs to bias constraints with negation pairs.

### 4. QuAcq Changes

Methods to update (all change `str` → `int` for constraint IDs):
- `learn()` — task type changes
- `_prune_rejecting_constraints()` — iterate `task.bias` (now `Set[int]`), lookup clauses via `task.constraint_clauses[assumption_id]`
- `_find_conflict()` — return `List[int]`
- `_quickxplain_constraints()` — operate on `List[int]`
- `_reduce_kb()` — **DELETE entirely** — replaced by direct REDUCE call
- `_build_result()` — return `InteractiveResult` with `List[int]`

### 5. FindScope + FindC Changes

- `find_scope()` — constraint IDs become `int`, scope logic unchanged (feature vars already `int`)
- `find_c()` — constraint pool is `List[int]`
- `_narrow_with_pool()` / `_narrow_with_sat()` — operate on `int`

### 6. InteractiveResult Changes

- `kb_constraints: List[str]` → `kb_assumption_ids: List[int]`
- Add `description_provider: Optional[DescriptionProvider]` for display
- `to_dict()` can output both IDs and names using DescriptionProvider

### 7. InteractiveRunner Changes

- `_run_oracle_mode()` — use `InteractiveModel.prepare()` instead of `InteractiveLearner.from_files()`
- Result handling uses DescriptionProvider for output/logging

## Reusable ConGen Infrastructure

| Component | Current ConGen usage | QuAcq can reuse? |
|-----------|---------------------|------------------|
| `Reduce.reduce()` | Direct call | ✅ Direct (no wrapper needed) |
| `NonIncrementalPySATChecker` | Used by REDUCE | ✅ Same |
| `DescriptionProvider` | Maps assumption ID → name | ✅ Same |
| `prepare_kb()` helper | Assigns assumption IDs to bias | ✅ Extract and share |
| `negate_cnf_tseitin()` | Generates negated clauses | ✅ Already shared |
| `BGData` | Packages BG assumptions | ✅ Same oracle pattern |

## Risks

1. **FindScope/FindC regression** — These algorithms use constraint vars (feature variables) which are already `int`. Changing constraint IDs from `str` to `int` requires careful distinction between "constraint assumption ID" and "feature variable ID". Mitigate: clear naming conventions.

2. **Eval pipeline impact** — `InteractiveResult` format change affects `result_loader.py`, `cross_validation.py`, `accuracy.py`. Need to update eval code.

3. **Test impact** — All interactive tests use string constraint IDs. All need updating.

## Implementation Phases (for plan)

1. **Phase 1**: Create `QuAcqTask`, `InteractiveModel`, `InteractiveTaskPreparation`
2. **Phase 2**: Update QuAcq algorithm (learn, prune, find_conflict, remove _reduce_kb)
3. **Phase 3**: Update FindScope + FindC
4. **Phase 4**: Update InteractiveResult + InteractiveRunner
5. **Phase 5**: Update eval pipeline (result_loader, accuracy, etc.)
6. **Phase 6**: Update tests
7. **Phase 7**: Remove old InteractiveTask + InteractiveLearner (cleanup)

## Success Criteria

- QuAcq produces identical KB results (by name, via DescriptionProvider)
- REDUCE called directly without conversion layer
- All tests pass
- Shared infrastructure (prepare_kb, DescriptionProvider, REDUCE) used by both algorithms
- No string constraint IDs in QuAcq pipeline

## Resolved Questions

1. **InteractiveLearner + InteractiveTask**: Keep as deprecated (deprecation warning), remove in separate cleanup commit
2. **QueryGenerator**: Remove `tested_c_id` return value — only return `config`. Simplifies interface.
3. **Cleanup phase**: Separate commit after migration verified
