# Exploration: pos_assignment_to_assumption and neg_assignment_to_assumption Usage in QuAcq

## Executive Summary

The assignment-to-assumption dictionaries (`pos_assignment_to_assumption` and `neg_assignment_to_assumption`) are Part 4 of the shared Assumption ID layout used for SAT-based feature assignment handling in QuAcq. These dicts map feature names to their positive/negative assignment assumption IDs and are created in FMOracleModel, propagated through BGData, copied to QuAcqTask, and consumed by QuAcq pruning logic.

---

## 1. CREATION & BUILD

### 1.1 FMOracleTaskPreparation.prepare() — Primary Creation Point

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py:173-265`

**Method:** `FMOracleTaskPreparation.prepare()` (lines 189-264)

**Key creation loop (lines 209-228):**

```python
pos_assignment_to_assumption = {}
neg_assignment_to_assumption = {}

for name, fid in model.variables.items():
    # a_pos: if active → feature must be true
    a_pos = id_assumption
    desc = f'{name}=true'
    result.set_kb.append([-a_pos, fid])
    
    result.assumptions.append(a_pos)
    provider.add_configuration_description(a_pos, desc)
    pos_assignment_to_assumption[name] = a_pos
    id_assumption += 1
    
    # a_neg: if active → feature must be false
    a_neg = id_assumption
    desc = f'{name}=false'
    result.set_kb.append([-a_neg, -fid])
    
    result.assumptions.append(a_neg)
    provider.add_configuration_description(a_neg, desc)
    neg_assignment_to_assumption[name] = a_neg
    id_assumption += 1
```

**For each feature:**
- Creates two assumption IDs: `a_pos` and `a_neg`
- `pos_assignment_to_assumption[feature_name] = a_pos` (assumption that makes feature true)
- `neg_assignment_to_assumption[feature_name] = a_neg` (assumption that makes feature false)
- Adds unit clauses: `[-a_pos, fid]` and `[-a_neg, -fid]`
- Stores in DiagnosisTask result and caches in model

**Line 230-231:** Store in FMOracleModel for later use
```python
model._pos_assignment_to_assumption = pos_assignment_to_assumption
model._neg_assignment_to_assumption = neg_assignment_to_assumption
```

**Line 257-258:** Package into BGData (immutable)
```python
pos_assignment_to_assumption=dict(pos_assignment_to_assumption),
neg_assignment_to_assumption=dict(neg_assignment_to_assumption),
```

---

## 2. DATA FLOW & PROPAGATION

### 2.1 Creation Hierarchy

```
FMOracleModel.prepare()
  ↓
  FMOracleTaskPreparation.prepare()
    ↓ Creates dicts, stores in:
    ├─ FMOracleModel._pos_assignment_to_assumption (line 230)
    ├─ FMOracleModel._neg_assignment_to_assumption (line 231)
    ├─ BGData.pos_assignment_to_assumption (line 257)
    └─ BGData.neg_assignment_to_assumption (line 258)
```

### 2.2 Extraction Path (Oracle → ConGen/QuAcq)

```
FeatureModelOracle.get_bg_data()  (line 103-105)
  ↓ Returns:
  BGData with:
    - pos_assignment_to_assumption
    - neg_assignment_to_assumption
    ↓ Used by:
    ├─ ConGenTaskPreparation.prepare() (conacq/algorithms/acqmss/task_preparation.py:88)
    └─ QuAcqTaskPreparation.prepare() (conacq/algorithms/quacq/task_preparation.py:93)
```

### 2.3 QuAcq-specific Flow

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py:69-139`

**In QuAcqTaskPreparation.prepare():**

**Lines 93-107:** Copy from BGData to QuAcqTask
```python
# Step 0: Copy BG data from Oracle (root constraint pair)
bg_data = oracle.get_bg_data()
result.set_kb.extend(bg_data.set_kb)
result.assumptions.extend(list(bg_data.assumptions))
result.negation_map.update(bg_data.negation_map)
...
# Copy Part 4 data from BGData (feature assignment assumptions)
result.assignment_clauses = list(bg_data.assignment_clauses)
result.assignment_assumptions = list(bg_data.assignment_assumptions)
result.pos_assignment_to_assumption = dict(bg_data.pos_assignment_to_assumption)
result.neg_assignment_to_assumption = dict(bg_data.neg_assignment_to_assumption)
```

---

## 3. WHERE DICTS ARE PASSED AS PARAMETERS

### 3.1 QuAcq.learn() Method Signature

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py:100-114`

```python
def learn(self,
          set_c: List[int],
          set_b: List[int],
          negation_map: Dict[int, int],
          background_clauses: List[List[int]],
          feature_ids: Dict[str, int],
          id_to_feature: Dict[int, str],
          constraint_clauses: Dict[int, List[List[int]]],
          negated_clauses: Dict[int, List[List[int]]],
          pos_assignment_to_assumption: Dict[str, int] = None,        # LINE 109
          neg_assignment_to_assumption: Dict[str, int] = None,        # LINE 110
          root_assumption: int = None,
          mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
          max_queries: int = 1000,
          ) -> QuAcqResult:
```

**Lines 127-128:** Documentation
```python
pos_assignment_to_assumption: Feature name -> pos assignment assumption ID (Part 4)
neg_assignment_to_assumption: Feature name -> neg assignment assumption ID (Part 4)
```

### 3.2 Parameter Extraction/Flattening

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/quacq_runner.py:51-65`

```python
def _learn_params_from_task(task) -> dict:
    """Extract flat learn() params from QuAcqTask."""
    return dict(
        set_c=task.set_c,
        ...
        pos_assignment_to_assumption=task.pos_assignment_to_assumption,  # LINE 62
        neg_assignment_to_assumption=task.neg_assignment_to_assumption,  # LINE 63
        root_assumption=task.set_b[0] if task.set_b else None,
    )
```

**Usage (line 182):** Extract from task and pass to QuAcq.learn()
```python
task_data = _learn_params_from_task(task)
...
quacq.learn(**task_data, mode='oracle', max_queries=self.max_queries)
```

---

## 4. HOW THEY ARE CONSUMED

### 4.1 SAT-Based Pruning (Part 4 Feature Assignment)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py:299-320`

**Method:** `_prune_rejecting_constraints()` (lines 300-320)

```python
def _prune_rejecting_constraints(self,
                                 remaining_bias: set,
                                 positive_example: Dict[str, bool],
                                 root_assumption: int,
                                 pos_map: Dict[str, int],                 # pos_assignment_to_assumption
                                 neg_map: Dict[str, int]) -> List[int]:   # neg_assignment_to_assumption
    """Remove constraints from remaining_bias that reject the positive example.
    
    Uses SAT-based consistency checking with Part 4 feature assignment
    assumptions, catching implied violations beyond pure Boolean evaluation.
    """
    config_assumptions = [pos_map[feat] if val else neg_map[feat]
                          for feat, val in positive_example.items()
                          if feat in pos_map]
    base = [root_assumption] + config_assumptions
    pruned = []
    for aid in list(remaining_bias):
        if not self.checker.is_consistent(base + [aid]):
            pruned.append(aid)
    remaining_bias -= set(pruned)
    return pruned
```

**Key logic (line 311-313):**
- For each feature in positive example:
  - If `value=True`: use `pos_map[feat]` (positive assignment assumption)
  - If `value=False`: use `neg_map[feat]` (negative assignment assumption)
- Combine with root assumption to form base assumptions
- Check consistency of each constraint against this base

**Invocation (line 204-208):**
```python
if pos_assignment_to_assumption and root_assumption is not None:
    pruned = self._prune_rejecting_constraints(
        remaining_bias, query,
        root_assumption, pos_assignment_to_assumption,
        neg_assignment_to_assumption)
else:
    pruned = self._prune_rejecting_constraints_legacy(...)
```

**Fallback (line 322-339):** Legacy Boolean evaluation when Part 4 unavailable

### 4.2 FMOracleModel Configuration Application

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py:108-131`

**Method:** `_config_to_assumptions()` (lines 108-119)

```python
def _config_to_assumptions(self, configuration) -> list:
    """Convert feature config to assignment assumption IDs."""
    items = configuration.elements.items() if hasattr(configuration, 'elements') else configuration.items()
    return [self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[feat]
            for feat, value in items]
```

**Method:** `with_configuration()` (lines 121-131)

```python
def with_configuration(self, configuration) -> 'FMOracleModel':
    """Apply feature config: updates set_c with base + assignment assumptions."""
    self.task.set_c = self._base_set_c + self._config_to_assumptions(configuration)
    return self
```

**Test usage (line 50-51 in test_oracle_model.py):**
```python
assert model._pos_assignment_to_assumption["f1"] in active
assert model._neg_assignment_to_assumption["f2"] in active
```

---

## 5. QUACQ CLASSES

### 5.1 QuAcqModel

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py:20-145`

**Purpose:** Model container for bias constraints and solver config (parallel to ConGenModel)

**Key fields:**
- `constraint_map`: Dict[str, List[List[int]]] - bias constraints
- `negated_constraint_map`: Dict[str, List[List[int]]] - negated forms
- `variables`: Dict[str, int] - feature name → SAT variable ID
- `next_available_id`: int - next free assumption ID
- `_task`: Optional[QuAcqTask] - populated after prepare()
- `_description_provider`: Optional[DescriptionProvider]

**Key methods:**
- `prepare(oracle)` (line 110-126): Delegates to QuAcqTaskPreparation
- `get_kb()` (line 91-94): Returns set_kb + assignment_clauses
- `get_assumptions()` (line 105-108): Returns assumptions + assignment_assumptions
- `resolve_kb()` (line 128-144): Convert assumption IDs → constraint names + clauses

### 5.2 QuAcqTask (Inherits from DiagnosisTask)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py:26-67`

**Dataclass inheriting from DiagnosisTask with additional fields:**

```python
@dataclass
class QuAcqTask(DiagnosisTask):
    """Immutable task for QuAcq constraint acquisition."""
    # Part 4: Feature assignment assumptions (for SAT-based pruning)
    assignment_clauses: List[List[int]] = field(default_factory=list)
    assignment_assumptions: List[int] = field(default_factory=list)
    pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)    # LINE 65
    neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)    # LINE 66
```

**Inherited from DiagnosisTask:**
- `set_c`: Bias constraint assumption IDs
- `set_b`: BG assumption IDs
- `set_kb`: Full KB with assumption guards
- `negation_map`: {assumption_id → negated_assumption_id}
- `assumptions`: All assumption IDs

**Additional QuAcq-specific fields:**
- `background_clauses`: Raw BG CNF clauses (no assumption guards)
- `feature_ids`: Dict[str, int] - feature name → SAT variable ID
- `id_to_feature`: Dict[int, str] - reverse mapping
- `constraint_clauses`: Dict[int, List[List[int]]] - assumption_id → raw clauses
- `negated_clauses`: Dict[int, List[List[int]]] - assumption_id → negated clauses

### 5.3 QuAcqTaskPreparation

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py:69-139`

**Purpose:** Prepares QuAcqTask from bias + oracle (no E+/E-)

**Assumption ID Layout (QuAcq owns Parts 5-6):**
```
Parts 1-4: Owned by Oracle (see OracleTaskPreparation)
Part 5:    Tseitin vars (negated bias constraints)     ← QuAcqTaskPreparation
Part 6:    Bias constraint assumptions (paired)       ← QuAcqTaskPreparation
```

**prepare() method (lines 78-139):**
1. Copy BG data from Oracle (root constraint pair)
2. Store raw BG clauses (without assumption guards)
3. Copy Part 4 data from BGData (lines 103-107)
4. Assign assumption IDs for bias constraints via prepare_kb()
5. Assign set_b and set_c from assumptions via _assign_sets()
6. Build constraint_clauses and negated_clauses mappings
7. Populate feature_ids/id_to_feature from oracle

### 5.4 QuAcqModelBuilder

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model_builder.py:13-82`

**Purpose:** Fluent builder for QuAcqModel with auto-prepare

**Flow (build() method, lines 46-74):**
1. Load bias from JSON → BiasIO
2. Create QuAcqModel
3. Set constraint_map and variables
4. **Compute negation at build time** (lines 66-70)
   ```python
   next_tseitin_var = self._oracle.get_bg_data().next_available_id
   for key, c in model.constraint_map.items():
       neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
       model.negated_constraint_map[f"NOT({key})"] = neg_clauses
   model.next_available_id = next_tseitin_var
   ```
5. Call model.prepare(oracle) - returns prepared task

---

## 6. CONFIG CONVERSION TO ASSUMPTION IDS

### 6.1 FMOracleModel._config_to_assumptions()

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py:108-119`

```python
def _config_to_assumptions(self, configuration) -> list:
    """Convert feature config to assignment assumption IDs.
    
    Args:
        configuration: Dict[str, bool] or Configuration object
    
    Returns:
        List of assumption IDs for the given feature assignments
    """
    items = configuration.elements.items() if hasattr(configuration, 'elements') else configuration.items()
    return [self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[feat]
            for feat, value in items]
```

### 6.2 QuAcq._prune_rejecting_constraints() (lines 311-313)

```python
config_assumptions = [pos_map[feat] if val else neg_map[feat]
                      for feat, val in positive_example.items()
                      if feat in pos_map]
```

---

## 7. COMPLETE DATA STRUCTURE HIERARCHY

```
Assumption ID Layout (Shared across Oracle/ConGen/QuAcq):
═════════════════════════════════════════════════════════

Part 1: Feature variable IDs (1..n)
        ├─ Generated by: FmToDiagPysat
        └─ Used by: All modules

Part 2: Tseitin vars (negated FM constraints)
        ├─ Generated by: FmToDiagPysat
        └─ Used by: Oracle, consistency checks

Part 3: FM constraint assumptions (paired)
        ├─ Generated by: FMOracleTaskPreparation.prepare()
        ├─ Format: [root, NOT(root), c2, NOT(c2), ...]
        ├─ Stored in: BGData
        └─ Used by: ConGen, QuAcq

Part 4: Feature assignment assumptions (paired)  ← pos/neg_assignment_to_assumption
        ├─ Generated by: FMOracleTaskPreparation.prepare() (lines 209-228)
        ├─ For each feature: [f1_pos, f1_neg, f2_pos, f2_neg, ...]
        ├─ Clauses: [-a_pos, fid], [-a_neg, -fid]
        ├─ Stored in: BGData.pos/neg_assignment_to_assumption
        ├─ Copied to: QuAcqTask.pos/neg_assignment_to_assumption
        └─ Used by: QuAcq._prune_rejecting_constraints()

Part 5: Tseitin vars (negated bias constraints)
        ├─ Generated by: ConGenModelBuilder (negate_cnf_tseitin)
        ├─ Or: QuAcqModelBuilder (negate_cnf_tseitin)
        └─ Used by: QueryGenerator (negated form)

Part 6: Bias constraint assumptions (paired)
        ├─ Generated by: ConGenTaskPreparation.prepare() or QuAcqTaskPreparation.prepare()
        └─ Used by: QuAcq learning
```

---

## 8. FILE REFERENCES

### Core Files
1. **FMOracleModel** (`conacq/oracle/fm_oracle_model.py`)
   - Lines 48-49: Instance variable declarations
   - Lines 206-231: Creation and storage in FMOracleTaskPreparation
   - Lines 108-131: Usage in _config_to_assumptions() and with_configuration()

2. **BGData** (`conacq/oracle/bg_data.py`)
   - Lines 35-39: Dataclass fields

3. **FeatureModelOracle** (`conacq/oracle/fm_oracle.py`)
   - Lines 103-105: get_bg_data() method

4. **QuAcqTask** (`conacq/algorithms/quacq/task_preparation.py`)
   - Lines 62-66: Dataclass field definitions

5. **QuAcqTaskPreparation** (`conacq/algorithms/quacq/task_preparation.py`)
   - Lines 93-107: Copy from BGData to QuAcqTask

6. **QuAcq** (`conacq/algorithms/quacq/quacq.py`)
   - Lines 109-110: Parameter definitions
   - Lines 204-208: Conditional invocation (Part 4 available?)
   - Lines 311-313: Conversion in _prune_rejecting_constraints()
   - Lines 300-320: _prune_rejecting_constraints() method

7. **QuAcqRunner** (`conacq/runners/quacq_runner.py`)
   - Lines 51-65: _learn_params_from_task() extraction
   - Lines 62-63: Parameter passing

8. **Tests** (`tests/test_quacq.py`)
   - Lines 43-57: _learn_params_from_task() fixture
   - Lines 54-55: Fixture usage
   - Lines 668-669, 779-783, 793-794, 804-809: Test assertions

### Related Files
- `conacq/algorithms/acqmss/task_preparation.py`: ConGen parallel
- `conacq/algorithms/quacq/quacq_model_builder.py`: QuAcqModel builder
- `conacq/algorithms/quacq/sat_utils.py`: SAT utilities

---

## 9. KEY INSIGHTS

1. **Part 4 is optional:** Dicts default to None/empty in QuAcq.learn() (lines 109-110)
2. **Fallback mechanism:** Legacy pruning (_prune_rejecting_constraints_legacy) used when Part 4 unavailable
3. **SAT-based advantage:** Part 4 captures implied violations beyond pure Boolean evaluation
4. **Immutable at QuAcqTask:** Frozen dataclass ensures consistency
5. **Dual origins:** FMOracleModel creates dicts, QuAcqModel copies from oracle (via BGData)
6. **Paired structure:** Every feature has pos + neg assumption IDs (Part 4 property)

---

## 10. SUMMARY TABLE

| Component | Role | Line |
|-----------|------|------|
| FMOracleTaskPreparation.prepare() | Creation | 206-231 |
| FMOracleModel._pos_assignment_to_assumption | Storage (instance) | 48, 230 |
| FMOracleModel._neg_assignment_to_assumption | Storage (instance) | 49, 231 |
| BGData.pos_assignment_to_assumption | Propagation container | 38 |
| BGData.neg_assignment_to_assumption | Propagation container | 39 |
| FeatureModelOracle.get_bg_data() | Extraction | 103-105 |
| QuAcqTask.pos_assignment_to_assumption | QuAcq storage | 65 |
| QuAcqTask.neg_assignment_to_assumption | QuAcq storage | 66 |
| QuAcqTaskPreparation.prepare() | Copy to QuAcqTask | 106-107 |
| QuAcq.learn() | Parameter acceptance | 109-110 |
| QuAcq._prune_rejecting_constraints() | Primary consumption | 300-320 |
| FMOracleModel._config_to_assumptions() | Secondary consumption | 108-119 |

