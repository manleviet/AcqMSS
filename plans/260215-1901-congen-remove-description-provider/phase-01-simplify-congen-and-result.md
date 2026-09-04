# Phase 1: Simplify CONGENResult & acquire()

## Context
- Parent: [plan.md](plan.md)
- Key file: `acqmss/algorithms/congen.py`

## Overview
- **Priority:** High (other phases depend on this)
- **Status:** complete
- **Description:** Remove DescriptionProvider from ConGen core, simplify CONGENResult to raw IDs only, add utility function for name resolution.

## Key Insights
- `kb_assumption_ids` already exists — `kb_constraints` (name strings) is redundant
- `_get_name()` closure inside acquire() is the only place DescriptionProvider is used
- After removing DescriptionProvider import, `acqmss.algorithms` no longer depends on `explanation.models.task_preparation`
- `save_result()` currently serializes names — needs provider param or callers handle serialization

## Requirements
- CONGENResult stores only raw IDs (no description strings)
- ConGen.acquire() has no knowledge of DescriptionProvider
- A utility function exists for callers to resolve names when needed
- save_result() still works (accepts optional provider)

## Architecture
```
Before:  ConGen.acquire(description_provider) -> CONGENResult(kb_constraints=["name1",...])
After:   ConGen.acquire()                     -> CONGENResult(redundant_ids=[3,...])
         resolve_congen_names(result, provider) -> {"kb": ["name1",...], "redundant": ["name3",...]}
```

## Related Code Files
- **Modify:** `acqmss/algorithms/congen.py`

## Implementation Steps

1. **Simplify CONGENResult dataclass** (line 39-49):
   - Remove `kb_constraints: List[str]`
   - Rename `redundant_constraints: List[str]` -> `redundant_ids: List[int]`
   - Keep `kb_assumption_ids`, `n_bias`, `n_mss`, `n_kb`, `bg_clauses`, `metadata`

2. **Clean acquire() method** (line 68-170):
   - Remove `description_provider` param from signature
   - Remove `_get_name()` helper (lines 145-148)
   - Remove `kb_names` and `redundant_names` variables (lines 150-151)
   - Update CONGENResult construction: use raw `kb` and `redundant` lists directly
   - Update empty-result path (line 111-120) to match new field names

3. **Update save_result()** (line 172-193):
   - Add `description_provider: Optional[DescriptionProvider] = None` param
   - If provider given: resolve names for JSON output
   - If not: serialize raw IDs as strings

4. **Add utility function** after CONGENResult class:
   ```python
   def resolve_congen_names(result: CONGENResult, provider) -> dict:
       """Resolve assumption IDs to human-readable names."""
       return {
           'kb': [provider.get_description(a) for a in result.kb_assumption_ids],
           'redundant': [provider.get_description(a) for a in result.redundant_ids],
       }
   ```

5. **Remove import**: `from explanation.models.task_preparation import DescriptionProvider` (line 32)
   - Only re-add in save_result if needed, or use duck typing

## Todo
- [x] Simplify CONGENResult dataclass
- [x] Clean acquire() — remove description_provider param and name resolution
- [x] Update save_result() to accept optional provider
- [x] Add resolve_congen_names() utility function
- [x] Remove unused import

## Success Criteria
- ConGen.acquire() signature has no description_provider
- CONGENResult has no string name fields
- resolve_congen_names() utility exists
- No `explanation.models` import in algorithm core (or minimal in save_result)

## Risk Assessment
- **Low:** Dataclass field renames may break unpacking — but no caller unpacks positionally

## Security Considerations
- None — internal refactoring only

## Next Steps
- Phase 2: Update all callers to use new API
