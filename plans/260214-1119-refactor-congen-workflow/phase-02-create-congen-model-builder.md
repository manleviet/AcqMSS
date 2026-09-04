# Phase 02: Create ConGenModelBuilder

## Context Links

- DiagnosisModelBuilder reference: `explanation/models/diagnosis_model_builder.py` (438 LOC)
- ConGenModel (modified in Phase 01): `acqmss/algorithms/congen_model.py`
- BiasIO: `acqmss/bias/bias_io.py`
- ExampleIO: `acqmss/examples/example_io.py`
- FeatureModelOracle: `acqmss/oracle/fm_oracle.py`

## Overview

- **Priority**: P1
- **Status**: completed
- **Description**: Create new `ConGenModelBuilder` class mirroring `DiagnosisModelBuilder` pattern. Encapsulates file loading, model creation, and calling `prepare()`.

## Key Insights

- DiagnosisModelBuilder uses classmethods for source (`from_fide`, `from_uvl`), fluent setters, then `build()` which creates model + calls `prepare()`
- ConGenModelBuilder differs: source is bias+FM files (not just FM), plus examples
- Builder encapsulates: BiasIO loading, ExampleIO loading, FeatureModelOracle for feature_ids, root extraction
- `build()` calls `prepare()` internally (like DiagnosisModelBuilder line 352)
- After build(), model is ready for `CheckerFactory.create_from_model(model)`

## Requirements

### Functional
- `from_files(bias_path, fm_path)` classmethod to set source
- `with_examples(pos_path, neg_path)` to set example file paths
- `with_examples_data(pos_list, neg_list)` to set example data directly
- `use_incremental(bool)` to set solver mode
- `build()` creates ConGenModel, calls prepare(), returns model
- Model ready for CheckerFactory after build()

### Non-functional
- New file: `acqmss/algorithms/congen_model_builder.py` (~120 LOC)
- Follow fluent builder pattern matching DiagnosisModelBuilder style
- Type hints on all public methods

## Architecture

```
ConGenModelBuilder
  +-- from_files(bias_path, fm_path) -> Self        # classmethod
  +-- with_examples(pos_path, neg_path) -> Self      # file paths
  +-- with_examples_data(pos, neg) -> Self           # direct data
  +-- use_incremental(bool) -> Self                  # solver mode
  +-- with_solver(name) -> Self                      # solver name
  +-- build() -> ConGenModel                         # creates + prepares
  |     1. _validate()
  |     2. Load bias via BiasIO
  |     3. Load examples via ExampleIO (if paths)
  |     4. Load oracle for feature_ids + root
  |     5. Create ConGenModel.from_bias_and_examples()
  |     6. Set model.use_incremental
  |     7. model.prepare(solver_name=..., profiler=...)
  |     8. Return model
  +-- _validate()                                    # check required fields
```

## Related Code Files

### Files to create
- `acqmss/algorithms/congen_model_builder.py` — new builder class

### Files to modify
- `acqmss/algorithms/__init__.py` — add ConGenModelBuilder export

### Reference files (read-only)
- `explanation/models/diagnosis_model_builder.py` — pattern to follow

## Implementation Steps

### Step 1: Create `congen_model_builder.py`

```python
"""Builder for creating configured ConGenModel instances.

Mirrors DiagnosisModelBuilder pattern. Encapsulates file loading,
model creation, and prepare() invocation.
"""
from typing import Dict, List, Optional

from .congen_model import ConGenModel


class ConGenModelBuilder:
    """Fluent builder for ConGenModel.

    Examples:
        # From files (most common)
        model = (ConGenModelBuilder
            .from_files('data/bias/model.json', 'data/fms/model.uvl')
            .with_examples('data/examples/pos.json', 'data/examples/neg.json')
            .use_incremental(True)
            .build())

        # From data (for cross-validation folds)
        model = (ConGenModelBuilder
            .from_files('data/bias/model.json', 'data/fms/model.uvl')
            .with_examples_data(pos_list, neg_list)
            .use_incremental(False)
            .build())

        # Subsequent folds (reuse existing model)
        task = model.prepare(
            positive_examples=fold2_pos,
            negative_examples=fold2_neg
        )
    """

    def __init__(self):
        # Source paths
        self._bias_path: Optional[str] = None
        self._fm_path: Optional[str] = None

        # Examples (file paths OR direct data)
        self._examples_pos_path: Optional[str] = None
        self._examples_neg_path: Optional[str] = None
        self._positive_examples: Optional[List[Dict[str, bool]]] = None
        self._negative_examples: Optional[List[Dict[str, bool]]] = None

        # Solver config
        self._use_incremental: bool = True
        self._solver_name: str = 'glucose4'

    # === Source Methods ===

    @classmethod
    def from_files(cls, bias_path: str, fm_path: str) -> 'ConGenModelBuilder':
        """Create builder from bias and feature model files.

        Args:
            bias_path: Path to bias JSON file
            fm_path: Path to feature model UVL file

        Returns:
            ConGenModelBuilder instance
        """
        builder = cls()
        builder._bias_path = bias_path
        builder._fm_path = fm_path
        return builder

    # === Example Methods ===

    def with_examples(self, pos_path: str, neg_path: str) -> 'ConGenModelBuilder':
        """Set example file paths (loaded during build).

        Args:
            pos_path: Path to positive examples JSON
            neg_path: Path to negative examples JSON

        Returns:
            Self for chaining
        """
        self._examples_pos_path = pos_path
        self._examples_neg_path = neg_path
        return self

    def with_examples_data(
            self,
            positive: List[Dict[str, bool]],
            negative: List[Dict[str, bool]]
    ) -> 'ConGenModelBuilder':
        """Set example data directly (for CV folds).

        Args:
            positive: List of positive example dicts
            negative: List of negative example dicts

        Returns:
            Self for chaining
        """
        self._positive_examples = positive
        self._negative_examples = negative
        return self

    # === Solver Config ===

    def use_incremental(self, enabled: bool = True) -> 'ConGenModelBuilder':
        """Set incremental solver mode.

        Args:
            enabled: True for incremental, False for non-incremental

        Returns:
            Self for chaining
        """
        self._use_incremental = enabled
        return self

    def with_solver(self, solver_name: str) -> 'ConGenModelBuilder':
        """Set SAT solver name.

        Args:
            solver_name: e.g., 'glucose4', 'minisat22'

        Returns:
            Self for chaining
        """
        self._solver_name = solver_name
        return self

    # === Build ===

    def build(self) -> ConGenModel:
        """Build and return fully configured ConGenModel.

        Steps:
        1. Validate builder state
        2. Load bias, examples, feature model
        3. Create ConGenModel
        4. Set solver config
        5. Call prepare() (includes GenerateNE)

        Returns:
            ConGenModel with task prepared and ready for CheckerFactory

        Raises:
            ValueError: If required fields missing
        """
        self._validate()

        # Load dependencies
        from conacq.bias import BiasIO
        from conacq.oracle import FeatureModelOracle

        oracle = FeatureModelOracle(self._fm_path)
        bias = BiasIO.load_from_json(self._bias_path)
        feature_ids = oracle.get_feature_ids()

        # Extract root for background knowledge
        root_name = oracle.get_root_feature()
        root_id = feature_ids.get(root_name)
        bg = [root_id] if root_id is not None else []

        # Resolve examples
        pos, neg = self._resolve_examples()

        # Convert bias to constraint dict
        bias_constraints = {c.id: c.clauses for c in bias.constraints}

        # Create model
        model = ConGenModel.from_bias_and_examples(
            bias_constraints=bias_constraints,
            positive_examples=pos,
            negative_examples=neg,
            feature_ids=feature_ids,
            background_knowledge=bg
        )
        model.use_incremental = self._use_incremental
        model.solver_name = self._solver_name

        # Prepare (includes GenerateNE)
        model.prepare(solver_name=self._solver_name)

        return model

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None or self._fm_path is None:
            raise ValueError(
                "Source must be specified (use from_files(bias_path, fide_fm_path))")

        has_paths = (self._examples_pos_path is not None
                     and self._examples_neg_path is not None)
        has_data = (self._positive_examples is not None
                    and self._negative_examples is not None)

        if not has_paths and not has_data:
            raise ValueError(
                "Examples must be specified (use with_examples() or with_examples_data())")

        if has_paths and has_data:
            raise ValueError(
                "Cannot specify both file paths and data for examples")

    def _resolve_examples(self):
        """Load examples from paths or return direct data."""
        if self._positive_examples is not None:
            return self._positive_examples, self._negative_examples

        from conacq.examples import ExampleIO
        examples = ExampleIO.load_json(self._examples_pos_path)
        # Assumption: pos_path is a combined file with both pos/neg
        # If separate files, adjust accordingly
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        return pos, neg
```

**Note**: The `_resolve_examples` method assumes `with_examples()` receives a single combined examples file (matching current ExampleIO pattern). If the API uses separate pos/neg files, adjust the implementation. Check `ExampleIO.load_json()` to confirm — current callers pass one file containing both E+ and E-.

### Step 2: Update `with_examples()` signature

Looking at `run_congen.py` line 114, `ExampleIO.load_json()` loads a single file with both positive and negative examples. Simplify:

```python
def with_examples(self, examples_path: str) -> 'ConGenModelBuilder':
    """Set examples file path (contains both E+ and E-).

    Args:
        examples_path: Path to examples JSON (both pos and neg)

    Returns:
        Self for chaining
    """
    self._examples_path = examples_path
    return self
```

And update `_resolve_examples()`:

```python
def _resolve_examples(self):
    if self._positive_examples is not None:
        return self._positive_examples, self._negative_examples

    from conacq.examples import ExampleIO
    examples = ExampleIO.load_json(self._examples_path)
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    return pos, neg
```

### Step 3: Update `__init__.py` exports

In `acqmss/algorithms/__init__.py`, add:

```python
from .congen_model_builder import ConGenModelBuilder
```

And add to `__all__`:

```python
'ConGenModelBuilder',
```

## Todo List

- [ ] Create `acqmss/algorithms/congen_model_builder.py`
- [ ] Implement `from_files()` classmethod
- [ ] Implement `with_examples()` (single file path)
- [ ] Implement `with_examples_data()` (direct data)
- [ ] Implement `use_incremental()` and `with_solver()`
- [ ] Implement `build()` with validation + prepare()
- [ ] Add to `__init__.py` exports
- [ ] Verify builder produces model satisfying CheckerModel

## Success Criteria

- Builder creates valid ConGenModel with task prepared
- `isinstance(model, CheckerModel)` is True
- `CheckerFactory.create_from_model(model)` returns valid checker
- Builder validates missing required fields
- Builder rejects mutually exclusive options

## Risk Assessment

- **Risk**: ExampleIO.load_json() API mismatch (single vs split files)
  - **Mitigation**: Verify ExampleIO interface; adjust `with_examples()` accordingly
- **Risk**: Oracle creation overhead in builder
  - **Mitigation**: Oracle is lightweight (only used for feature_ids); acceptable

## Security Considerations

- File paths validated by underlying loaders (BiasIO, ExampleIO, Oracle)
- No new security surface

## Next Steps

- Phase 03 modifies ConGen.acquire() signature
- Phase 04 updates callers to use builder
