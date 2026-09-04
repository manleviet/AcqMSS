# Phase 6: Update Documentation

## Context Links

- Phase 5: `phase-05-delete-update-tests.md`
- Docs: `docs/quacq.md`, `docs/codebase-summary.md`, `docs/code-standards.md`

## Overview

- **Date**: 2026-02-28
- **Priority**: P2
- **Status**: completed
- **Description**: Update documentation to reflect QueryProvider merger, FindC simplification, removed classes

## Key Insights

- docs/quacq.md references ExampleProvider (line 52), QueryGenerator (lines 28, 277), _narrow_with_pool behavior
- docs/codebase-summary.md lists both files in example_generators table (lines 86-92)
- docs/code-standards.md references ExampleProvider in DI pattern example (lines 286-315)
- All three docs need QueryProvider references and updated API examples

## Requirements

### Functional
- Replace ExampleProvider/QueryGenerator references with QueryProvider
- Update API examples showing new DI pattern
- Update FindC documentation (no pool narrowing)
- Update file inventory (removed files, new file)
- Add QueryProvider to "Removed Classes" table

### Non-Functional
- Keep docs concise, only update changed sections

## Related Code Files

### Files to modify
- `docs/quacq.md`
- `docs/codebase-summary.md`
- `docs/code-standards.md`

## Implementation Steps

### Step 1: Update docs/quacq.md

**Section "Implementation" (near line 28)**:
- Replace `conacq/example_generators/query_generator.py -- GenerateQuery heuristics` with `conacq/example_generators/query_provider.py -- QueryProvider (unified pool + SAT)`

**Section "Example-Based Mode" (near line 52)**:
- Replace `conacq/example_generators/example_provider.py -- ExampleProvider for batch examples` with reference to QueryProvider pool mode

**Section "FindC" (near lines 87-101)**:
- Remove "Pool-Based Narrowing" subsection
- Simplify to: "Uses DiscriminatingGenerator to narrow candidates (paper Algorithm 3)"

**Section "Relation to Codebase" (near lines 147-158)**:
- Update file list: remove query_generator.py and example_provider.py, add query_provider.py

**Section "Removed Classes" table (near line 289)**:
- Add ExampleProvider -> QueryProvider (pool mode)
- Add QueryGenerator -> QueryProvider (SAT mode)

**Section "Example-Based Mode" code example (near line 336)**:
- Update to use QueryProvider:
```python
from conacq.example_generators import QueryProvider

query_provider = QueryProvider(pool=examples_list, seed=42)
quacq = QuAcq.for_examples(checker, oracle, query_provider)

# Pool only
result = quacq.learn(..., mode='example_only', ...)

# Pool + SAT fallback
result = quacq.learn(..., mode='example_first', ...)
```

**Section "Query & Example Generation" (near line 277)**:
- Replace QueryGenerator and ExampleProvider entries with single QueryProvider entry

### Step 2: Update docs/codebase-summary.md

**example_generators table (lines 86-92)**:
- Remove `query_generator.py` row (262 LOC)
- Remove `example_provider.py` row (~120 LOC)
- Add `query_provider.py` row (~200 LOC)
- Update LOC totals

**Changes section**:
- Add entry for this refactoring session

### Step 3: Update docs/code-standards.md

**DI pattern section (around lines 286-315)**:
- Replace `example_provider: ExampleProvider` with `query_provider: QueryProvider`
- Update `for_examples()` factory signature
- Update code example

### Step 4: Verify no stale references

Grep entire docs/ directory for:
- `ExampleProvider` -- should find 0 matches (except in Removed Classes table)
- `QueryGenerator` -- should find 0 matches (except in Removed Classes table)
- `query_generator.py` -- should find 0 matches
- `example_provider.py` -- should find 0 matches

## Todo List

- [ ] Update docs/quacq.md (all sections)
- [ ] Update docs/codebase-summary.md (file inventory, LOC)
- [ ] Update docs/code-standards.md (DI examples)
- [ ] Grep docs/ for stale references

## Success Criteria

- No stale ExampleProvider/QueryGenerator references (except Removed Classes)
- API examples show QueryProvider usage
- File inventory accurate
- FindC docs reflect paper-only narrowing (no pool)

## Risk Assessment

- **Low risk**: Documentation only, no code changes
- Stale references in docs are cosmetic but confusing

## Security Considerations

- N/A

## Next Steps

- Plan complete. All phases done.
