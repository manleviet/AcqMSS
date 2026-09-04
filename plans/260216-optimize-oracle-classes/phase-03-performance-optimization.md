# Phase 3: Performance Optimization

## Context Links

- [Class Internals](research/researcher-01-class-internals.md) — performance findings
- [Callers & Dependencies](research/researcher-02-callers-dependencies.md) — call frequency analysis
- [fm_oracle.py](../../conacq/oracle/fm_oracle.py) — double FM loading
- [extractor.py](../../conacq/oracle/ground_truth.py) — calls get_constraint_descriptions() once

## Overview

- **Priority**: Medium
- **Status**: complete
- **Effort**: 45m
- **Description**: Eliminate double FM loading in FeatureModelOracle, cache `get_constraint_descriptions()`, and apply lazy initialization for the FM object. These changes reduce init time and prevent O(n) re-traversal on repeated calls.

## Key Insights

- **Double FM loading**: `__init__` loads FM twice:
  1. Line 52: `FMOracleModel.from_fm(fm_path)` internally calls `UVLReader(path).transform()` (in `build()`)
  2. Line 57: `UVLReader(fm_path).transform()` again for `self.fm` (used only for descriptions)
- **No caching**: `get_constraint_descriptions()` does full FM traversal every call. `OracleData.from_oracle()` calls it once, but `generate_examples.py` never calls it — so caching mainly benefits evaluation workflows.
- **Lazy init opportunity**: `self.fm` is only needed when `get_constraint_descriptions()`, `get_leaf_features()`, or `get_root_feature()` are called. Most callers (ConGen, QuAcq) never use these methods.

## Requirements

### Functional
- FM loaded at most once during FeatureModelOracle initialization
- `get_constraint_descriptions()` result cached after first call
- `self.fm` loaded lazily (only when description/leaf/root methods called)

### Non-Functional
- Init time improved (1 fewer UVLReader call)
- Repeated `get_constraint_descriptions()` calls O(1) after first

## Architecture

```
Before:
  __init__():
    FMOracleModel.from_fm(path).build()  → loads FM internally (UVLReader)
    UVLReader(path).transform()          → loads FM AGAIN for self.fm

After:
  __init__():
    FMOracleModel.from_fm(path).build()  → loads FM internally
    self._fm = None                      → lazy, not loaded yet
    self._constraint_descriptions = None → cached on first access

  _get_fm():                             → lazy loader, uses UVLReader once
  get_constraint_descriptions():         → returns cached result
```

## Related Code Files

### Files to Modify
- `acqmss/oracle/fm_oracle.py` — lazy FM init, caching

### Files Unchanged
- `acqmss/oracle/fm_oracle_model.py` — no changes needed
- `acqmss/oracle/extractor.py` — calls unchanged public API
- `acqmss/oracle/constraint_description.py` — new file from Phase 2, no changes

## Implementation Steps

### Step 1: Lazy FM initialization

Replace eager FM loading with lazy property.

```python
# BEFORE (in __init__):
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
self.fm = UVLReader(fm_path).transform()

# AFTER (in __init__):
self._fm = None  # Lazy loaded for description extraction
self._constraint_descriptions_cache: Optional[Set[str]] = None
```

Add lazy loader property:

```python
@property
def fm(self):
    """Lazy-load FM for description extraction."""
    if self._fm is None:
        from flamapy.metamodels.fm_metamodel.transformations import UVLReader
        self._fm = UVLReader(self.fm_path).transform()
    return self._fm
```

**Backward compatibility**: Any code accessing `oracle.fm` directly will trigger lazy load transparently. Property access is compatible with attribute access patterns.

### Step 2: Cache get_constraint_descriptions()

```python
# BEFORE:
def get_constraint_descriptions(self) -> Set[str]:
    from conacq.oracle.constraint_description import extract_constraint_descriptions
    return extract_constraint_descriptions(self.fm)


# AFTER:
def get_constraint_descriptions(self) -> Set[str]:
    """Extract constraint descriptions from FM (cached)."""
    if self._constraint_descriptions_cache is None:
        from conacq.oracle.constraint_description import extract_constraint_descriptions
        self._constraint_descriptions_cache = extract_constraint_descriptions(self.fm)
    return self._constraint_descriptions_cache
```

### Step 3: Update get_leaf_features() and get_root_feature()

These already access `self.fm` — with the property approach, they will trigger lazy load automatically. No code changes needed.

Verify:

```python
def get_leaf_features(self) -> Set[str]:
  return {f.name for f in self.fm.get_variables() if f.is_leaf()}  # self.fm triggers lazy load


def get_root_feature(self) -> str:
  return self.fm.root.name  # self.fm triggers lazy load
```

### Step 4: Consider eliminating double-load entirely (OPTIONAL)

An alternative approach: extract the FM object from `FMOracleModel.build()` and store it. This would require modifying `build()` to return or expose the FM.

Current `build()` code:
```python
def build(self) -> 'FMOracleModel':
    fm = UVLReader(self._fm_path).transform()
    fm_model = FmToDiagPysat(fm, create_negation=True).transform()
    # fm is discarded after this point
```

**Decision**: SKIP this optimization. It would couple FeatureModelOracle to FMOracleModel internals (exposing FM through FMOracleModel). The lazy init approach (Step 1) achieves the same goal: FM loaded only when needed, and many callers (ConGen, QuAcq) never need it.

If future profiling shows double-load is a bottleneck (unlikely — UVL parsing is fast), revisit then.

### Step 5: Run tests

```bash
PYTHONPATH=. pytest tests/test_oracle_model.py tests/test_congen.py -v
```

### Step 6: Verify lazy loading works

Manual verification:
```python
# FM should NOT be loaded yet
oracle = FeatureModelOracle('data/fms/model.uvl')
assert oracle._fm is None  # Lazy, not loaded

# FM loaded on first description call
descs = oracle.get_constraint_descriptions()
assert oracle._fm is not None
assert oracle._constraint_descriptions_cache is not None

# Second call returns cached
descs2 = oracle.get_constraint_descriptions()
assert descs is descs2  # Same object
```

## Todo List

- [ ] Replace `self.fm = UVLReader(...)` with `self._fm = None` in `__init__`
- [ ] Add `self._constraint_descriptions_cache = None` to `__init__`
- [ ] Add `fm` property with lazy loading
- [ ] Add caching to `get_constraint_descriptions()`
- [ ] Remove `from flamapy...import UVLReader` from `__init__` (move to property)
- [ ] Verify `get_leaf_features()` and `get_root_feature()` work via property
- [ ] Run tests — all pass
- [ ] Manual verification of lazy loading behavior

## Success Criteria

- FM loaded at most once (lazy, on demand)
- `get_constraint_descriptions()` cached after first call
- No `UVLReader` import at module level in fm_oracle.py (stays lazy)
- All tests pass
- FeatureModelOracle init is faster for ConGen/QuAcq callers that never call description methods

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `self.fm` attribute access breaks | Low | High | Property is transparent; `oracle.fm.root` works same |
| Cache staleness | None | N/A | FM is immutable after load; cache never stale |
| Thread safety of lazy init | Low | Low | Single-threaded usage pattern in this codebase |

## Security Considerations

None — performance optimization, no security impact.

## Next Steps

- Phase 4: Architecture refinements (set_c consolidation, with_configuration cleanup)
