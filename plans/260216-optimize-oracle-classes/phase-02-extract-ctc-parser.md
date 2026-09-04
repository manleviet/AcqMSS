# Phase 2: Extract CTC Description Parser

## Context Links

- [Class Internals](research/researcher-01-class-internals.md) — SRP violation analysis
- [fm_oracle.py](../../conacq/oracle/fm_oracle.py) — `_parse_ctc_to_description` at lines 239-307
- [extractor.py](../../conacq/oracle/ground_truth.py) — OracleData uses `get_constraint_descriptions()`
- [Code Standards](../../docs/code-standards.md) — Oracle module conventions (lines 375-447)

## Overview

- **Priority**: High (reduces fm_oracle.py to ~200 LOC target)
- **Status**: complete
- **Effort**: 45m
- **Description**: Extract `_parse_ctc_to_description()`, `_get_feature_name()`, and hierarchical constraint extraction from `FeatureModelOracle` into a dedicated `constraint_description.py` module. This addresses the SRP violation where FeatureModelOracle handles oracle interface + FM parsing + CTC description extraction.

## Key Insights

- `_parse_ctc_to_description` is 68 lines of AST traversal — independent concern from oracle validation
- `_get_feature_name` is a pure helper (12 lines), no state dependency
- `get_constraint_descriptions()` (lines 199-237) traverses FM features — only depends on `self.fm`
- Two lazy imports inside methods (`from flamapy.core.models.ast import ASTOperation`) should become module-level in new file
- `OracleData.from_uvl()` and `OracleData.from_oracle()` both call `get_constraint_descriptions()` — interface preserved

## Requirements

### Functional
- Create `acqmss/oracle/constraint_description.py` (~80 LOC)
- Move CTC parsing logic to standalone function(s)
- `FeatureModelOracle.get_constraint_descriptions()` delegates to new module
- Public API unchanged — callers see no difference

### Non-Functional
- New file under 200 LOC
- fm_oracle.py drops to ~180 LOC after extraction
- Module-level imports (no lazy imports in new file)

## Architecture

```
Before:
  FeatureModelOracle
  ├── is_valid()           (oracle concern)
  ├── get_features()       (oracle concern)
  ├── get_constraint_descriptions()  (description concern)
  ├── _parse_ctc_to_description()    (description concern)
  └── _get_feature_name()            (description concern)

After:
  FeatureModelOracle
  ├── is_valid()
  ├── get_features()
  └── get_constraint_descriptions()  → delegates to extract_constraint_descriptions(fm)

  constraint_description.py (NEW)
  ├── extract_constraint_descriptions(fm) -> Set[str]
  ├── _parse_ctc_to_description(ctc) -> Optional[str]
  └── _get_feature_name(node) -> Optional[str]
```

## Related Code Files

### Files to Create
- `acqmss/oracle/constraint_description.py` — new module

### Files to Modify
- `acqmss/oracle/fm_oracle.py` — remove extracted methods, add delegation
- `acqmss/oracle/__init__.py` — optionally export `extract_constraint_descriptions`

### Files Unchanged (but verify)
- `acqmss/oracle/extractor.py` — calls `oracle.get_constraint_descriptions()`, no change needed
- `tests/test_oracle_model.py` — no direct tests for description extraction

## Implementation Steps

### Step 1: Create constraint_description.py

Create `acqmss/oracle/constraint_description.py`:

```python
"""
Constraint description extraction from feature models.

Parses FM hierarchical relations and cross-tree constraints (CTCs)
into human-readable description strings matching bias format.
"""

from typing import Optional, Set

from flamapy.core.models.ast import ASTOperation


def extract_constraint_descriptions(fm) -> Set[str]:
    """Extract constraint descriptions from a feature model.

    Returns descriptions in format matching bias:
    - "parent --mandatory--> child"
    - "parent --optional--> child"
    - "parent --alternative--> [child1, child2, ...]"
    - "parent --or--> [child1, child2, ...]"
    - "feature1 requires feature2"
    - "feature1 excludes feature2"

    Args:
        fm: Feature model object (flamapy FeatureModel)

    Returns:
        Set of constraint description strings
    """
    descriptions = set()

    # Hierarchical constraints from feature relationships
    for feature in fm.get_variables():
        for relation in feature.get_relations():
            if relation.is_mandatory():
                for child in relation.children:
                    descriptions.add(f"{feature.name} --mandatory--> {child.name}")
            elif relation.is_optional():
                for child in relation.children:
                    descriptions.add(f"{feature.name} --optional--> {child.name}")
            elif relation.is_alternative():
                children_names = [c.name for c in relation.children]
                descriptions.add(f"{feature.name} --alternative--> {children_names}")
            elif relation.is_or():
                children_names = [c.name for c in relation.children]
                descriptions.add(f"{feature.name} --or--> {children_names}")

    # Cross-tree constraints
    for ctc in fm.get_constraints():
        desc = _parse_ctc_to_description(ctc)
        if desc:
            descriptions.add(desc)

    return descriptions


def _parse_ctc_to_description(ctc) -> Optional[str]:
    """Parse cross-tree constraint to description format.

    Supports requires (A => B) and excludes (!(A & B)) patterns.
    Falls back to string representation for unrecognized patterns.
    """
    ast = ctc.ast
    if ast is None:
        return None

    root = ast.root

    # Handle requires: A => B
    if root.data == ASTOperation.IMPLIES:
        left, right = root.left, root.right
        if left and right:
            left_name = _get_feature_name(left)
            right_name = _get_feature_name(right)
            if left_name and right_name:
                return f"{left_name} requires {right_name}"

    # Handle excludes: !(A & B)
    if root.data == ASTOperation.NOT:
        inner = root.left
        if inner and inner.data == ASTOperation.AND:
            left, right = inner.left, inner.right
            if left and right:
                left_name = _get_feature_name(left)
                right_name = _get_feature_name(right)
                if left_name and right_name:
                    names = sorted([left_name, right_name])
                    return f"{names[0]} excludes {names[1]}"

    # Handle excludes: A => !B
    if root.data == ASTOperation.IMPLIES:
        left, right = root.left, root.right
        if right and right.data == ASTOperation.NOT:
            left_name = _get_feature_name(left)
            right_name = _get_feature_name(right.left)
            if left_name and right_name:
                names = sorted([left_name, right_name])
                return f"{names[0]} excludes {names[1]}"

    # Handle OR patterns (flamapy UVL representation)
    if root.data == ASTOperation.OR:
        left, right = root.left, root.right
        if left and right:
            # OR(NOT(A), NOT(B)) == A excludes B
            if left.data == ASTOperation.NOT and right.data == ASTOperation.NOT:
                left_name = _get_feature_name(left.left)
                right_name = _get_feature_name(right.left)
                if left_name and right_name:
                    names = sorted([left_name, right_name])
                    return f"{names[0]} excludes {names[1]}"

            # OR(NOT(A), B) == A requires B
            if left.data == ASTOperation.NOT:
                left_name = _get_feature_name(left.left)
                right_name = _get_feature_name(right)
                if left_name and right_name:
                    return f"{left_name} requires {right_name}"

    # Fallback: use constraint string representation
    return str(ctc)


def _get_feature_name(node) -> Optional[str]:
    """Extract feature name from AST node."""
    if node is None:
        return None
    if node.data is None or not isinstance(node.data, ASTOperation):
        return str(node.data) if node.data else None
    return None
```

### Step 2: Update FeatureModelOracle.get_constraint_descriptions()

Replace the method body and remove extracted methods:

```python
# BEFORE (lines 199-320 in fm_oracle.py):
# get_constraint_descriptions() + _parse_ctc_to_description() + _get_feature_name()

# AFTER:
def get_constraint_descriptions(self) -> Set[str]:
    """Extract constraint descriptions from FM.

    Returns descriptions in format matching bias.

    Returns:
        Set of constraint descriptions
    """
    from conacq.oracle.constraint_description import extract_constraint_descriptions
    return extract_constraint_descriptions(self.fm)
```

Remove `_parse_ctc_to_description()` (lines 239-307) and `_get_feature_name()` (lines 309-320) from fm_oracle.py.

### Step 3: Update __init__.py (optional)

Add export if external callers want direct access:

```python
from .constraint_description import extract_constraint_descriptions
```

Add to `__all__`: `'extract_constraint_descriptions'`

### Step 4: Run tests

```bash
PYTHONPATH=. pytest tests/test_oracle_model.py tests/test_congen.py -v
```

Also test description extraction end-to-end via extractor if integration tests exist:
```bash
PYTHONPATH=. pytest tests/ -k "oracle" -v
```

## Todo List

- [ ] Create `acqmss/oracle/constraint_description.py` with extracted functions
- [ ] Replace `get_constraint_descriptions()` in fm_oracle.py with delegation call
- [ ] Remove `_parse_ctc_to_description()` from fm_oracle.py
- [ ] Remove `_get_feature_name()` from fm_oracle.py
- [ ] Update `__init__.py` exports
- [ ] Verify fm_oracle.py is ~180 LOC
- [ ] Verify constraint_description.py is ~80 LOC
- [ ] Run tests — all pass

## Success Criteria

- fm_oracle.py: ~180 LOC (down from ~250 after Phase 1)
- constraint_description.py: ~80 LOC, self-contained
- No lazy imports (`from flamapy...`) inside methods of new file — module-level only
- `OracleData.from_uvl()` and `OracleData.from_oracle()` work unchanged
- All tests pass

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missing CTC pattern in extraction | Low | Medium | Exact same logic, just moved |
| Import cycle | Low | High | constraint_description.py has no oracle imports |
| OracleData breaks | Low | Medium | Uses public `get_constraint_descriptions()`, unchanged API |

## Security Considerations

None — pure refactor, same logic.

## Next Steps

- Phase 3: Add caching to `get_constraint_descriptions()` (now cleanly separated)
