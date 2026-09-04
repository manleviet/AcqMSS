# Scout Report: Negation Map & Assignment-to-Assumption Analysis

**Exploration Date**: 2026-02-28 04:49 UTC  
**Work Context**: /Users/manleviet/Development/GitHub/AcqMSS  
**Relates to**: Plan 260227-2307-negation-build-time

---

## 1. QuAcqTask — Immutable Data Container

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` (lines 26-61)

### Data Structure
```python
@dataclass
class QuAcqTask(DiagnosisTask):
    # Inherited from DiagnosisTask:
    set_c: List[int]              # Bias constraint assumption IDs
    set_b: List[int]              # BG assumption IDs
    set_kb: List[List[int]]        # Full KB with assumption guards
    negation_map: Dict[int, int]   # {assumption_id -> negated_id}
    assumptions: List[int]         # All assumption IDs in order
    
    # QuAcq-specific (raw clauses, no guards):
    background_clauses: List[List[int]]
    constraint_clauses: Dict[int, List[List[int]]]
    negated_clauses: Dict[int, List[List[int]]]
    feature_ids: Dict[str, int]
    id_to_feature: Dict[int, str]
```

### Key Design Property
- **Immutable**: Defined as `@dataclass` (no `unsafe_hash=True` — truly immutable)
- **Two-layer clause storage**: 
  - `set_kb` contains assumption-guarded clauses like `[-a_pos, clause...]`
  - `constraint_clauses[aid]` contains raw clauses (no guards) — used by _prune_rejecting_constraints
  - `negated_clauses[aid]` contains raw negated clauses — used by QueryGenerator

---

## 2. QuAcqModel — Builder-Pattern Configuration

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` (lines 20-143)

### Fields
```python
class QuAcqModel:
    constraint_map: Dict[str, List[List[int]]]     # Constraint name → clauses
    negated_constraint_map: Dict[str, List[List[int]]]  # "NOT(name)" → negated clauses
    variables: Dict[str, int]                      # Feature name → SAT var ID
    next_available_id: int                         # Assumption ID start for Part 6
    use_incremental: bool                          # CheckerModel protocol
    _task: Optional[QuAcqTask]
    _description_provider: Optional[DescriptionProvider]
```

### Critical Methods
- **`prepare(oracle: FeatureModelOracle) -> QuAcqTask`** (lines 108-124)
  - Invokes `QuAcqTaskPreparation.prepare(self, oracle)`
  - Returns prepared QuAcqTask with assumption IDs assigned
  - Sets both `_task` and `_description_provider`

- **`resolve_kb(kb_assumption_ids: List[int]) -> (names, clauses)`** (lines 126-142)
  - Reverse-maps assumption IDs back to constraint names
  - Used to convert learned KB to human-readable form

### Builder Pattern Usage
```python
oracle = FeatureModelOracle('model.uvl')
model = (QuAcqModelBuilder
         .from_bias('bias.json')
         .with_oracle(oracle)
         .build())  # Returns prepared QuAcqModel
task = model.task  # Access prepared QuAcqTask
```

---

## 3. FMOracleModel — Assignment-to-Assumption Dictionaries

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py` (lines 17-254)

### The Core Dictionaries (Lines 48-49)
```python
self._pos_assignment_to_assumption: Dict[str, int] = {}  # feature → a_pos
self._neg_assignment_to_assumption: Dict[str, int] = {}  # feature → a_neg
```

### Creation in FMOracleTaskPreparation.prepare() (Lines 206-230)

**Positive assignments (feature=true)**:
```python
for name, fid in model.variables.items():
    a_pos = id_assumption  # Fresh assumption ID
    result.set_kb.append([-a_pos, fid])  # If a_pos active, fid must be true
    result.assumptions.append(a_pos)
    pos_assignment_to_assumption[name] = a_pos  # ← DICT ENTRY
    id_assumption += 1
```

**Negative assignments (feature=false)**:
```python
    a_neg = id_assumption
    result.set_kb.append([-a_neg, -fid])  # If a_neg active, fid must be false
    result.assumptions.append(a_neg)
    neg_assignment_to_assumption[name] = a_neg  # ← DICT ENTRY
    id_assumption += 1
```

### Purpose
- **Convert feature configurations to assumption IDs** for consistency checking
- **Part 4 of Assumption ID Layout**: Variable assignment assumptions (paired)
  - Format: `[f1=true, f1=false, f2=true, f2=false, ...]`
  - Each feature gets two assumption IDs (positive and negative)

### Usage Pattern
Only used in `_config_to_assumptions()` method (see below)

---

## 4. _config_to_assumptions() — The Key Consumer

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py` (lines 108-119)

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

### Data Flow
- **Input**: Feature config like `{'root': True, 'child': False}`
- **Output**: Assumption IDs like `[1003, 1005]` (if root's a_pos is 1003, child's a_neg is 1005)
- **Semantic**: "If these assumption IDs are active, the configuration's constraints apply"

### Called By (Only Place)
- `with_configuration()` method (line 130): Updates `task.set_c` with assignment assumptions
- Used during `is_valid()` check to apply feature configuration constraints

---

## 5. _prune_rejecting_constraints() — The Critical Algorithm

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 287-304)

### Complete Method
```python
@count_calls('prune_calls')
def _prune_rejecting_constraints(self,
                                 constraint_clauses: Dict[int, List[List[int]]],
                                 feature_ids: Dict[str, int],
                                 remaining_bias: set,
                                 positive_example: Dict[str, bool]) -> List[int]:
    """Remove constraints from remaining_bias that reject the positive example."""
    # Step 1: Convert example config to SAT assignment
    assumptions_list = config_to_assumptions(positive_example, feature_ids)
    assignment = {abs(lit): lit > 0 for lit in assumptions_list}
    
    # Step 2: Check which constraints are violated
    pruned = []
    for aid in list(remaining_bias):
        clauses = constraint_clauses.get(aid, [])
        if violates_clauses(clauses, assignment):
            pruned.append(aid)
    
    # Step 3: Update mutable state
    remaining_bias -= set(pruned)
    return pruned
```

### Key Points
- **Line 294**: `config_to_assumptions()` uses feature_ids (NOT the FMOracleModel's dict)
- **Line 295**: Converts SAT literals to assignment dict: `{var_id: bool}`
- **Line 300**: `violates_clauses()` checks if assignment satisfies constraint clauses
- **Called at**: Line 198 in `learn()` method after oracle answers "YES" to query
- **Purpose**: Eliminate constraints that are violated by positive example

### SAT Utilities
**Imported from sat_utils**:
- `config_to_assumptions(config, feature_ids)` — Feature config → SAT literals
- `violates_clauses(clauses, assignment)` — Check constraint violation

---

## 6. violates_clauses() — SAT Evaluation

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/sat_utils.py` (lines 48-61)

```python
def violates_clauses(clauses: List[List[int]],
                     assignment: Dict[int, bool]) -> bool:
    """Check if assignment violates constraint clauses."""
    for clause in clauses:
        clause_satisfied = False
        for lit in clause:
            var = abs(lit)
            if var in assignment:
                if (lit > 0 and assignment[var]) or (lit < 0 and not assignment[var]):
                    clause_satisfied = True
                    break
        if not clause_satisfied:
            return True  # ← Found unsatisfied clause
    return False  # ← All clauses satisfied
```

### Logic
- **Clause satisfied**: At least one literal is true under assignment
- **Returns True**: If ANY clause is unsatisfied (== constraint is violated)
- **Returns False**: If ALL clauses are satisfied

### Input Format
- **clauses**: Raw CNF like `[[1, -2], [2, 3]]` (from constraint_clauses dict)
- **assignment**: Dict mapping var_id to bool, e.g., `{1: True, 2: False}`

---

## 7. BGData — Bridge from Oracle to QuAcq

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/bg_data.py` (lines 1-27)

```python
@dataclass(frozen=True)
class BGData:
    """Root BG constraint data extracted post-preparation from Oracle.
    
    Fields:
        set_kb: Assumption-guarded clauses for root constraint + negated form
        assumptions: (root_assumption_id, negated_root_assumption_id)
        negation_map: {root_id: negated_root_id}
        descriptions: {root_id: "desc", neg_id: "NOT(desc)"}
        next_available_id: First free ID after Oracle Parts 3+4
    """
    set_kb: List[List[int]]
    assumptions: Tuple[int, int]
    negation_map: Dict[int, int]
    descriptions: Dict[int, str]
    next_available_id: int
```

### Creation (FMOracleTaskPreparation.prepare(), Lines 242-249)
```python
model._bg_data = BGData(
    set_kb=result.set_kb[:2],  # First pair (root assumption pair)
    assumptions=(result.assumptions[0], result.assumptions[1]),
    negation_map={result.assumptions[0]: result.assumptions[1]},
    descriptions=provider.get_descriptions_for(
        [result.assumptions[0], result.assumptions[1]]),
    next_available_id=id_assumption,
)
```

### Consumption (QuAcqTaskPreparation.prepare(), Lines 87-92)
```python
bg_data = oracle.get_bg_data()
result.set_kb.extend(bg_data.set_kb)  # Copy assumption-guarded clauses
result.assumptions.extend(list(bg_data.assumptions))  # Copy root pair IDs
result.negation_map.update(bg_data.negation_map)  # Copy negation for root
for aid, desc in bg_data.descriptions.items():
    provider.add_constraint_description(aid, desc)
```

### Data Flow
1. **Oracle** creates BGData with root constraint pair + next available ID
2. **FeatureModelOracle.get_bg_data()** exposes it
3. **QuAcqTaskPreparation** copies root pair into QuAcqTask
4. **QuAcqTask.set_b** contains `[root_id]` only

---

## 8. Assumption ID Layout (Oracle owns Parts 1-4)

**Shared Architecture** (documented in FMOracleTaskPreparation, lines 176-185):

```
Part 1: Feature variable IDs (1..n)
        ← From FM during UVLReader conversion
        
Part 2: Tseitin variables (negated FM constraints)
        ← From FmToDiagPysat with create_negation=True
        
Part 3: FM constraint assumptions (paired)
        ← Created in FMOracleTaskPreparation (lines 200-201)
        [root, NOT(root), c2, NOT(c2), c3, NOT(c3), ...]
        Each constraint gets two IDs (assumption + negation)
        
Part 4: Variable assignment assumptions (paired)
        ← Created in FMOracleTaskPreparation (lines 208-227)
        [f1=true, f1=false, f2=true, f2=false, ...]
        Each feature gets two IDs (_pos and _neg dicts)
```

**QuAcq continues from Part 5** (QuAcqTaskPreparation):
```
Part 5: Tseitin variables (negated bias constraints)
        ← During prepare_kb() call
        
Part 6: Bias constraint assumptions (paired)
        ← During prepare_kb() call
        [b1, NOT(b1), b2, NOT(b2), ...]
```

**BGData bridge**: Extracts Part 3's first pair (root) + end-of-Part-4 ID for QuAcq

---

## 9. FMOracleModel — CheckerModel Protocol Implementation

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py` (lines 77-97)

### Protocol Compliance
```python
@property
def use_incremental(self) -> bool:
    return self._use_incremental

def get_kb(self) -> List[List[int]]:
    return self.task.set_kb

def get_assumptions(self) -> List[int]:
    return self.task.assumptions
```

### CheckerModel Protocol Definition
**Location**: `/Users/manleviet/Development/GitHub/AcqMSS/explanation/operations/algorithms/checker.py` (lines 22-33)

```python
@runtime_checkable
class CheckerModel(Protocol):
    """Protocol for models compatible with CheckerFactory."""
    use_incremental: bool
    def get_kb(self) -> List[List[int]]: ...
    def get_assumptions(self) -> List[int]: ...
```

**Both FMOracleModel and QuAcqModel satisfy this protocol** (can be used with `CheckerFactory.create_from_model()`)

---

## 10. ConsistencyChecker Implementations

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/explanation/operations/algorithms/checker.py` (lines 36-245)

### AbstractBase (Lines 36-89)
```python
class ConsistencyChecker(ABC):
    def is_consistent(self, set_c: List) -> bool: ...  # Abstract
    def is_consistent_test_cases(self, set_c: List, set_tc: List, stop_at_first_violation: bool) -> List: ...
    def copy(self): ...  # For multiprocessing
    def cleanup(self) -> None: ...  # Release resources
```

### Implementations
1. **IncrementalPySATChecker** (lines 91-134)
   - Persistent solver across multiple calls
   - Reuses solver state
   - Line 107: `solver.solve(assumptions=final_assumptions)`

2. **NonIncrementalPySATChecker** (lines 137-164)
   - Fresh solver per call
   - No state reuse
   - Line 152: `solver = Solver(..., bootstrap_with=self.set_kb)`

3. **SAT4JChecker** (lines 167-217)
   - External Java solver via subprocess
   - Encodes assumptions as unit clauses

---

## 11. QuAcq.learn() Method Signature & Flow

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 100-267)

### Complete Signature
```python
@measure_time('quacq_runtime')
@count_calls('quacq_calls')
def learn(self,
          set_c: List[int],                                    # Bias constraint IDs
          set_b: List[int],                                    # BG assumption IDs
          set_kb: List[List[int]],                             # Full KB (unused, for protocol)
          negation_map: Dict[int, int],                        # {assumption_id -> negated_id}
          assumptions: List[int],                              # All assumption IDs
          background_clauses: List[List[int]],                 # Raw BG clauses
          feature_ids: Dict[str, int],                         # Feature → var ID
          id_to_feature: Dict[int, str],                       # Var ID → feature
          constraint_clauses: Dict[int, List[List[int]]],      # assumption_id → raw clauses
          negated_clauses: Dict[int, List[List[int]]],         # assumption_id → negated clauses
          mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
          max_queries: int = 1000) -> QuAcqResult
```

### Mutable State (Lines 135-139)
```python
remaining_bias = set(set_c)          # Shrinks as constraints eliminated
learned_kb: List[int] = []           # Grows as constraints accepted
n_queries = 0                        # Tracking
query_history: List[...] = []        # Query log
```

### Main Algorithm Loop (Lines 151-248)
1. **Get query** (lines 161-178)
   - Oracle mode: `query_generator.generate()` with `constraint_clauses`, `negated_clauses`
   - Example mode: Pull from `example_provider.next_example()`

2. **Oracle answer** (line 191)
   - `answer = self.oracle.is_valid(query)`

3. **If POSITIVE** (lines 197-200)
   - `_prune_rejecting_constraints()` removes constraints
   - No FindScope/FindC

4. **If NEGATIVE** (lines 201-244)
   - `find_scope()` → `find_c()` → Add constraint to learned_kb

5. **Convergence** (lines 246-256)
   - Empty bias: return learned_kb
   - Reduce algorithm applies negation_map for redundancy detection

### Return Value (Lines 258-267)
```python
self.result = QuAcqResult(
    kb_assumption_ids=kb,
    n_queries=n_queries,
    convergence_reason=convergence_reason,
    query_history=query_history
)
```

---

## 12. Test Integration Pattern

**File & Location**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` (lines 43-56)

```python
def _learn_params_from_task(task):
    """Extract flat learn() params from QuAcqTask."""
    return dict(
        set_c=task.set_c,
        set_b=task.set_b,
        set_kb=task.set_kb,
        negation_map=task.negation_map,
        assumptions=task.assumptions,
        background_clauses=task.background_clauses,
        feature_ids=task.feature_ids,
        id_to_feature=task.id_to_feature,
        constraint_clauses=task.constraint_clauses,
        negated_clauses=task.negated_clauses,
    )

# Usage:
task = prepared_model.task
task_data = _learn_params_from_task(task)
result = quacq.learn(**task_data, mode='oracle', max_queries=5)
```

### Test Case (Lines 452-479)
- Creates QueryGenerator + DiscriminatingGenerator from task data
- Calls `QuAcq.for_oracle(checker, oracle, query_gen, discrim_gen)`
- Executes `quacq.learn(**task_data, ...)`
- Verifies result.kb_assumption_ids can be resolved via `prepared_model.resolve_kb()`

---

## Summary: Data Flow Diagram

```
FeatureModelOracle
  ↓ loads FM from .uvl
  ↓ FMOracleModel.from_fm().build()
    ├─ UVLReader → FM object
    ├─ FmToDiagPysat (Parts 1-2)
    └─ FMOracleTaskPreparation.prepare()
        ├─ Creates _pos_assignment_to_assumption
        ├─ Creates _neg_assignment_to_assumption
        ├─ Part 3: FM constraint assumptions
        ├─ Part 4: Variable assignment assumptions
        └─ BGData = {root pair + next_id}
  ↓
  ↓ oracle.get_bg_data() → BGData
  ↓
  QuAcqModelBuilder.from_bias().with_oracle().build()
  ↓ QuAcqModel.prepare(oracle)
    ↓ QuAcqTaskPreparation.prepare()
      ├─ Copy BGData (set_b, negation_map from root)
      ├─ Part 5-6: Bias constraint assumptions
      └─ Build constraint_clauses + negated_clauses
  ↓
  ↓ QuAcqTask (immutable, all data in)
  ↓
  ↓ Extract params via _learn_params_from_task()
  ↓
  QuAcq.learn() algorithm
  ├─ positive answer → _prune_rejecting_constraints()
  │  ├─ convert_to_assumptions(config, feature_ids)
  │  ├─ violates_clauses(constraint_clauses[aid], assignment)
  │  └─ remove from remaining_bias
  │
  ├─ negative answer → find_scope() + find_c()
  │  └─ add to learned_kb
  │
  └─ Reduce(negation_map) → final KB
  ↓
  QuAcqResult(kb_assumption_ids, n_queries, reason)
```

---

## Critical Distinctions

| Concept | Owner | Purpose | Structure |
|---------|-------|---------|-----------|
| **_pos_assignment_to_assumption** | FMOracleModel | Feature→assumption (positive) | `{feat_name: assumption_id}` |
| **_neg_assignment_to_assumption** | FMOracleModel | Feature→assumption (negative) | `{feat_name: assumption_id}` |
| **negation_map** (on Task) | QuAcqTask | Assumption→negated assumption | `{assumption_id: negated_id}` |
| **constraint_clauses** | QuAcqTask | Bias constraints (raw, no guards) | `{assumption_id: [[lit, ...], ...]}` |
| **negated_clauses** | QuAcqTask | Negated bias constraints | `{assumption_id: [[lit, ...], ...]}` |
| **set_kb** | QuAcqTask | KB with assumption guards | `[[-a, clause...], ...]` |

---

## Unresolved Questions

1. **REFINEMENT OPPORTUNITY**: Does _prune_rejecting_constraints really need to reconstruct assignment from config_to_assumptions? Could we cache it?
2. **REFINEMENT OPPORTUNITY**: The feature_ids parameter is passed separately from constraint_clauses — could be grouped?
3. **BUILD-TIME ANALYSIS**: Where exactly should the negation dict building be optimized? In prepare() or in builder?

---

**Report Generated**: 2026-02-28  
**Status**: Scout complete, ready for architecture design phase
