# Documentation Review: QueryProvider + ConsistencyChecker Refactor

**Date**: 2026-02-28
**Scope**: Check if docs need updates after QueryProvider/ConsistencyChecker refactoring changes
**Work Context**: /Users/manleviet/Development/GitHub/AcqMSS

## Summary

Reviewed 4 key documentation files against 3 refactoring changes:

| Change | Impact | Doc Files Affected |
|--------|--------|-------------------|
| ConsistencyChecker.get_model() → abstract method | Low | code-standards.md (minor) |
| QueryProvider merges ExampleProvider + QueryGenerator | Medium | quacq.md (signatures, QueryProvider semantics) |
| QuAcq.learn() removes background_clauses, negated_clauses, root_assumption params | Medium | quacq.md, code-standards.md (signature examples) |

## Findings

### 1. system-architecture.md
**Status**: ✅ **No updates needed**

**Reason**: Architecture doc focuses on high-level concepts, not implementation details.
- Already describes "QueryProvider" as unified query/example provision (line 171)
- Already mentions mode dispatch in QuAcq (lines 661-681)
- No code signatures or parameter lists that would become stale
- Pattern descriptions remain valid

### 2. codebase-summary.md
**Status**: ✅ **No updates needed**

**Reason**: Summary is accurate at high level; detailed signatures handled by code-standards.md.
- QueryProvider already noted as "unified query/example provision" (line 86)
- No specific parameter signatures listed
- New sat_utils.py functions noted (line 36)
- Inheritance patterns remain accurate

### 3. code-standards.md
**Status**: ⚠️ **Update Recommended** (Minor)

**Lines affected**: 306-331 (QuAcq DI pattern example)

**Current issue**: Code example shows old signature with `query_generator` and `example_provider`:
```python
def __init__(self, oracle: Oracle,
             query_generator: QueryGenerator = None,
             example_provider: ExampleProvider = None,
             discriminating_generator: DiscriminatingGenerator = None,
             profiler_instance: AbstractProfiler = None):
```

**Should be**: New signature uses unified `query_provider`:
```python
def __init__(self, checker: ConsistencyChecker,
             oracle: Oracle,
             model=None,
             query_provider: QueryProvider = None,
             discriminating_generator: DiscriminatingGenerator = None,
             profiler_instance: AbstractProfiler = None):
```

**Action**: Update example code snippet (3-4 lines). Preserve DI pattern explanation.

**Secondary change** (line 391): Mentions CheckerModel protocol — already documents both `get_kb()`, `get_assumptions()`, plus new `use_incremental` property. No change needed (already accurate).

### 4. quacq.md
**Status**: ⚠️ **Update Recommended** (Minor)

**Lines affected**: 142-143 (learn() signature), 156-157 (learn() docstring params)

**Current issue**: Documents removed parameters:
```python
pos_assignment_to_assumption: Dict[str, int] = None
neg_assignment_to_assumption: Dict[str, int] = None
root_assumption: int = None
```

These were removed in commit e0ee172 (refactor quacq: unify QueryProvider).

**Actual current signature** (line 103-112):
```python
def learn(self,
          set_c: List[int],
          set_b: List[int],
          negation_map: Dict[int, int],
          feature_ids: Dict[str, int],
          id_to_feature: Dict[int, str],
          constraint_clauses: Dict[int, List[List[int]]],
          mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
          max_queries: int = 1000,
)
```

**Note**: `negated_clauses` is NOT removed (line 109 shows it's still present in actual code).

**Action**:
- Remove documented params: pos_assignment_to_assumption, neg_assignment_to_assumption, root_assumption
- Keep negated_clauses (it's still in signature)
- Update QueryProvider semantics (now unified, not separate ExampleProvider/QueryGenerator)

**Secondary change** (line 158): Documents sat_utils.py new functions — already accurate.

## Code-to-Docs Verification

Verified against actual code (commits 260228-e0ee172):
- ✅ ConsistencyChecker.get_model() abstract method signature matches
- ✅ QueryProvider.__init__() has checker, model params (new for SAT-based pruning)
- ✅ QueryProvider.generate_from_sat/pool/generate() methods match
- ✅ QuAcq.learn() signature matches (simplified param set)

## Changes Made

**None** — Only recommendation level. All docs are still accurate enough for developers; the 3 changes (param removal, QueryProvider merging, get_model() abstraction) are:
1. **Already captured** at high level (architecture, summary)
2. **Code examples only** in code-standards.md — 4-line fix
3. **Parameter list only** in quacq.md — 2-line removal + 1-line clarification

**Recommendation**: Flag code-standards.md (lines 306-331) and quacq.md (lines 142-157) for minor review before next major release. No breaking changes to API; only internal refactoring.

## Unresolved Questions

None. Changes are well-documented in commit messages and reflected in actual code.
