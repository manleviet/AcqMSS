# Phase 5: Refactor OracleData to GroundTruthData

## Context Links
- [Plan overview](plan.md)
- [FM reading duplication analysis](research/researcher-02-fm-reading-duplication.md)
- OracleData: `acqmss/oracle/extractor.py`
- Evaluator: `acqmss/eval/evaluator.py`

## Overview
- **Priority**: P2
- **Status**: complete
- **Effort**: 1h

Rename `OracleData` to `GroundTruthData`. Refactor `from_uvl()` to read FM directly via UVLReader + FmToDiagPysat instead of creating a FeatureModelOracle just for extraction. Remove `from_oracle()`/`from_fm_oracle()` entirely (YAGNI).
<!-- Updated: Validation Session 1 - from_fm_oracle() removed per user decision -->

## Key Insights
- `OracleData.from_uvl()` creates a `FeatureModelOracle` solely to extract 4 pieces of data, then discards it
- This instantiates a SAT solver, checker, and full model — heavy overhead for data extraction
- All needed data (descriptions, clauses, feature_map, root_feature) can be read directly from FM
- `Evaluator` is the only consumer of OracleData via `Evaluator.from_files()` (line 271)
- `acqmss/eval/__init__.py` re-exports OracleData

## Requirements

### Functional
1. Rename `OracleData` to `GroundTruthData`
2. `from_uvl()` reads FM directly: UVLReader + FmToDiagPysat + extract_constraint_descriptions
3. `from_oracle()`/`from_fm_oracle()` **REMOVED** (YAGNI — only `from_uvl()` used)
4. All references updated: Evaluator, eval/__init__.py, tests

### Non-functional
- No SAT solver instantiation for pure data extraction
- Lighter import chain (no CheckerFactory dependency)

## Architecture

### Before
```
OracleData.from_uvl(path)
  → FeatureModelOracle(path)     # heavy: UVL → CNF → solver → checker
    → oracle.get_constraint_descriptions()
    → oracle.get_cnf_clauses()
    → oracle.get_feature_ids()
    → oracle.get_root_feature()
  → del oracle
```

### After
```
GroundTruthData.from_uvl(path)
  → UVLReader(path).transform()           # light: just parse FM
  → FmToDiagPysat(fm).transform()         # CNF conversion only
  → extract_constraint_descriptions(fm)   # description extraction
  → model.variables                       # feature map
  → fm.root.name                          # root feature
```

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `acqmss/oracle/extractor.py` | Rename class, refactor `from_uvl()`, remove `from_oracle()` |
| `acqmss/oracle/__init__.py` | Update export: `OracleData` → `GroundTruthData` |
| `acqmss/eval/evaluator.py` | Update import and usage of `GroundTruthData` |
| `acqmss/eval/__init__.py` | Update re-export |
| `acqmss/algorithms/interactive/learner.py` | If any reference to OracleData (check — likely none) |

## Implementation Steps

### 1. Refactor `acqmss/oracle/extractor.py`

```python
"""
Ground truth data extractor for evaluation.

Extracts constraint descriptions and CNF clauses from feature models
directly (without instantiating a full oracle).
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict
from pathlib import Path


@dataclass
class GroundTruthData:
    """Ground truth data extracted from feature model."""
    descriptions: Set[str] = field(default_factory=set)
    clauses: List[List[int]] = field(default_factory=list)
    clause_set: Set[Tuple[int, ...]] = field(default_factory=set)
    feature_map: Dict[str, int] = field(default_factory=dict)
    root_feature: str = ""

    @classmethod
    def from_uvl(cls, uvl_path: Path) -> 'GroundTruthData':
        """Load ground truth data directly from UVL file.

        Reads FM, converts to CNF, extracts descriptions — no solver needed.
        """
        from flamapy.metamodels.fm_metamodel.transformations import UVLReader
        from explanation.transformations.fm_to_diag_pysat import FmToDiagPysat
        from conacq.oracle.constraint_description import extract_constraint_descriptions

        uvl_path = Path(uvl_path)
        fm = UVLReader(str(uvl_path)).transform()
        fm_model = FmToDiagPysat(fm, create_negation=False).transform()

        descriptions = extract_constraint_descriptions(fm)
        clauses = [clause for clauses in fm_model.constraint_map.values()
                   for clause in clauses]
        clause_set = {tuple(sorted(c)) for c in clauses}
        feature_map = dict(fm_model.variables)
        root_feature = fm.root.name

        return cls(
            descriptions=descriptions,
            clauses=clauses,
            clause_set=clause_set,
            feature_map=feature_map,
            root_feature=root_feature
        )

    # from_fm_oracle() REMOVED — YAGNI
```

### 2. Update `acqmss/oracle/__init__.py`

```python
from .extractor import GroundTruthData

__all__ = [
    ...
    'GroundTruthData',  # replaces 'OracleData'
    ...
]
```

### 3. Update `acqmss/eval/evaluator.py`

```python
from conacq.oracle.ground_truth import GroundTruthData


class Evaluator:
    def __init__(self, oracle: GroundTruthData, bias: BiasData):
        ...

    @classmethod
    def from_files(cls, oracle_path, bias_path):
        oracle = GroundTruthData.from_uvl(Path(oracle_path))
        ...
```

### 4. Update `acqmss/eval/__init__.py`

Replace `OracleData` with `GroundTruthData` in imports and `__all__`.

## Todo List
- [x] Rename OracleData to GroundTruthData in extractor.py
- [x] Refactor `from_uvl()` to read FM directly (no FeatureModelOracle)
- [x] Remove `from_oracle()` entirely
- [x] Update `acqmss/oracle/__init__.py` export
- [x] Update Evaluator import and type annotation
- [x] Update `acqmss/eval/__init__.py` re-export
- [x] Search for any other `OracleData` references and update

## Success Criteria
- `GroundTruthData.from_uvl()` works without importing FeatureModelOracle
- `from_uvl()` does not instantiate a solver or checker
- Evaluator works with GroundTruthData
- No remaining references to `OracleData` anywhere in codebase

## Risk Assessment
- **Risk**: `FmToDiagPysat(fm, create_negation=False)` may produce different clause output than oracle path
- **Mitigation**: Both paths use same FmToDiagPysat. Oracle path uses `create_negation=True` but `get_raw_fm_clauses()` returns same base clauses. Verify clause output matches in tests.
- **Risk**: Missing `from_oracle()` callers after rename
- **Mitigation**: Grep for all `OracleData` and `from_oracle` references before rename.

## Next Steps
- Phase 6: Clean up FeatureModelOracle + wrappers
