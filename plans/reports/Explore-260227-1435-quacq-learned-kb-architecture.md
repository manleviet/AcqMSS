# QuAcq Algorithm Architecture: learned_kb Mutation & Data Flow Analysis

## Executive Summary

**learned_kb is MUTABLE and MUTATED during learning.**

- **QuAcqTask** treats `learned_kb` as an **input** that is **incrementally built** during algorithm execution via `add_to_kb()`
- **QuAcq algorithm** is the **primary mutator** that fills `learned_kb` as constraints are learned
- **REDUCE** reads from `learned_kb` and produces final KB (non-mutating)
- This pattern **differs fundamentally** from ConGen, which separates input/output concerns

---

## 1. learned_kb Usage in QuAcqTask

### Location
**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` (lines 51-54, 77-82, 84-87)

### Definition & Purpose
```python
@dataclass
class QuAcqTask(DiagnosisTask):
    """Task for QuAcq constraint acquisition."""
    
    # Learned KB assumption IDs (MUTABLE)
    learned_kb: List[int] = field(default_factory=list)
```

**Initial state**: Empty list `[]`  
**Final state**: Contains all learned constraint assumption IDs after algorithm execution  
**Type**: `List[int]` — assumption-based identifier (not constraint names)

### Mutation Points in QuAcqTask

#### 1. **add_to_kb(assumption_id: int) → None**
```python
def add_to_kb(self, assumption_id: int) -> None:
    """Add a constraint assumption ID to the learned KB."""
    if assumption_id not in self.learned_kb:
        self.learned_kb.append(assumption_id)
```
- **Appends** constraint ID to `learned_kb`
- Prevents duplicates (idempotent)
- Called exclusively by **QuAcq.learn()** algorithm

#### 2. **Query History as Side Effect**
```python
def record_query(self, config: Dict[str, bool], answer: bool, 
                 source: str = 'main') -> None:
    """Record a membership query and its answer."""
    self.n_queries += 1  # Also mutates n_queries counter
    self.query_history.append((config.copy(), answer, source))
```
- Mutates `query_history` and `n_queries` as byproducts of learning
- Tracks audit trail of all queries for evaluation

---

## 2. How QuAcq Algorithm Uses learned_kb

### Location
**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 144-221, 224-345)

### Pattern: Read-Process-Mutate Cycle

The QuAcq algorithm follows this pattern:

```
WHILE bias is not empty:
  1. Generate query from current bias
  2. Ask oracle/examples
  3. IF answer is positive:
       Prune rejecting constraints from bias
  4. ELSE (negative answer):
       Find minimal conflict set via QuickXPlain
       FOR each constraint in conflict:
         ► task.add_to_kb(c_id)        [MUTATION]
         ► task.remove_from_bias([c_id]) [MUTATION]
  5. UNTIL: max_queries OR bias exhausted
```

### Key Methods That Mutate learned_kb

#### **1. learn() — Oracle-based learning**
```python
def learn(self, task: QuAcqTask, oracle: Oracle, ...) -> QuAcqResult:
    """Run QuAcq with oracle-based membership queries."""
    while task.bias:
        # ...
        if answer:
            pruned = self._prune_rejecting_constraints(task, query)
        else:
            conflict = self._find_conflict(task, query)
            if conflict:
                for c_id in conflict:
                    task.add_to_kb(c_id)         # ← MUTATION
                    task.remove_from_bias(conflict)
```
**Lines 200-214**: Direct mutations via `add_to_kb()`

#### **2. learn_from_examples() — Example-based learning**
```python
def learn_from_examples(self, task: QuAcqTask, ...) -> QuAcqResult:
    """Run QuAcq with ExampleProvider + FindScope/FindC."""
    while task.bias:
        # ...
        if is_valid:
            pruned = self._prune_rejecting_constraints(task, query)
        else:
            # FindScope + FindC resolution
            if c_id is not None:
                task.add_to_kb(c_id)              # ← MUTATION
                task.remove_from_bias([c_id])
            else:
                # Fallback to QuickXPlain
                conflict = self._find_conflict(task, query)
                if conflict:
                    for c_id in conflict:
                        task.add_to_kb(c_id)      # ← MUTATION
                    task.remove_from_bias(conflict)
```
**Lines 322-333**: Mutations via FindScope/FindC or fallback

#### **3. _find_conflict() — Conflict Resolution (Internal)**
```python
def _find_conflict(self, task: QuAcqTask, negative_example: Dict) -> List[int]:
    """Find minimal conflict set using QuickXPlain on assumption IDs."""
    # Returns list of constraint IDs (not added to KB here)
    # Caller adds these to KB
    return conflict
```
- **Does NOT mutate** `learned_kb` directly
- Returns constraint IDs to caller for processing
- Pattern: Read from `bias`, return conflict set

#### **4. _apply_reduce() — Redundancy Elimination (Post-learning)**
```python
def _apply_reduce(self, task) -> List[int]:
    """Apply REDUCE directly using assumption IDs from QuAcqTask."""
    if not task.learned_kb:
        return []
    
    reduce = Reduce(checker, self.profiler)
    redundant, non_redundant = reduce.reduce(
        set_b_prime=task.learned_kb,  # ← READ (not mutate)
        set_neg_tv=[],
        set_bg=task.set_b,
        negation_map=task.negation_map
    )
    return non_redundant  # Return final KB
```
- **Reads** from `task.learned_kb` (immutable at this point)
- REDUCE doesn't mutate `learned_kb`
- Returns filtered version

---

## 3. Data Flow: Who Creates, Reads, Writes

### Creation Flow

```
QuAcqModelBuilder.build()
  ↓
QuAcqModel.prepare(oracle)
  ↓
QuAcqTaskPreparation.prepare(model, oracle)
  ↓ 
QuAcqTask.__init__()
  → learned_kb = []  [INITIALIZED EMPTY]
  → bias = {c1, c2, ..., cn}  [populated from bias constraints]
```

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` (lines 195-262)

### Reading Flow

```
QuAcq.learn() / learn_from_examples()
  ├─ Reads: task.bias (shrinks during learning)
  ├─ Reads: task.feature_ids (static)
  ├─ Reads: task.constraint_clauses (static)
  ├─ Reads: task.negation_map (static)
  ├─ Reads: task.set_b, task.set_kb (static — from Oracle)
  └─ Writes: task.learned_kb (grows via add_to_kb)

QuAcq._apply_reduce()
  ├─ Reads: task.learned_kb (at end of learning)
  └─ Returns: filtered KB
```

### Writing Flow

```
During QuAcq.learn() execution:
  While bias not empty:
    If negative_example:
      conflict = _find_conflict(task, query)
      For each c_id in conflict:
        task.add_to_kb(c_id)        [SINGLE WRITE PATTERN]
        task.remove_from_bias([c_id])
    task.record_query(config, answer)  [SIDE EFFECT]

At end of learn():
  final_kb = _apply_reduce(task)  [READ learned_kb, return filtered]
```

---

## 4. Comparison: QuAcq vs ConGen vs DiagnosisTask/TestCaseTask

### QuAcqTask (Interactive Learning)
- **learned_kb**: Mutable, built incrementally via `add_to_kb()`
- **bias**: Mutable, shrunk via `remove_from_bias()`
- **set_kb, set_b**: Immutable inputs from Oracle
- **Pattern**: Algorithm-centric (QuAcq controls mutations)

### ConGenTask (Batch Learning)
```python
@dataclass
class ConGenTask(TestCaseTask):
    # Inherits from TestCaseTask (no additional fields)
    pass
```

- **set_c** (bias): Input to ConGen algorithm (not mutated by algorithm)
- **set_tc** (E+): Input (static)
- **set_tv** (E-): Input (static)
- **set_neg_tv** (NE): Input (pre-computed by GenerateNE)
- **Return value**: ConGenResult with `kb_assumption_ids` (new list)
- **Pattern**: Functional (algorithm returns new KB, doesn't mutate task)

**ConGen flow**:
```python
# congen.py
def acquire(self, set_b: List[int], set_bg: List[int], 
            set_tc: List[int], set_neg_tv: List[int]) -> ConGenResult:
    # set_b, set_tc, set_neg_tv are INPUT only (never mutated)
    b_prime = acqmss.find_mss(delta=[], set_b=set_b, ...)
    redundant, kb = reduce.reduce(set_b_prime=b_prime, ...)
    return ConGenResult(kb_assumption_ids=kb, ...)
    # ↑ Returns NEW list, doesn't mutate input task
```

### DiagnosisTask / TestCaseTask (Base Classes)
```python
@dataclass
class DiagnosisTask:
    """Base class for a diagnosis task."""
    set_c: List = field(default_factory=list)        # Candidate constraints
    set_b: List = field(default_factory=list)        # Background knowledge
    set_kb: List = field(default_factory=list)       # Full KB with assumptions
    negation_map: Dict = field(default_factory=dict)
    assumptions: List = field(default_factory=list)

@dataclass
class TestCaseTask(DiagnosisTask):
    """Adds test case fields (for KBDiag, WipeOutR_T)."""
    set_tc: List = field(default_factory=list)   # Positive test cases
    set_tv: List = field(default_factory=list)   # Negative test cases
    set_neg_tv: List = field(default_factory=list)  # Negated negatives
    set_neg_tc: List = field(default_factory=list)  # Negated positives
```

**Purpose**: Data containers for diagnosis/redundancy operations  
**Mutation**: Only populated during preparation, not by algorithms  
**User**: Algorithms read these as **immutable inputs**

---

## 5. Mutation Safety Analysis

### Is learned_kb Safe to Mutate During Learning?

**YES**, with caveats:

1. **Single-threaded guarantee**: Each algorithm instance owns one task
2. **Linear growth**: Only `add_to_kb()` and `remove_from_bias()` touch `learned_kb`/`bias`
3. **Deterministic order**: Mutation order = query order = algorithm logic
4. **No concurrent access**: Task is not shared between threads/processes

**Caveats**:
- Task must be created **fresh per run** (not reused across learning rounds)
- Runner implements this: `build()` creates new model+task **each call**

### Why QuAcqTask Mutates but ConGenTask Doesn't

| Aspect | QuAcq | ConGen |
|--------|-------|--------|
| **Learning style** | Interactive (incremental) | Batch (all examples upfront) |
| **Task lifespan** | Lives for entire learning session | Ephemeral input to algorithm |
| **KB construction** | Grows via algorithm decisions | Produced by algorithm function |
| **Reducer access** | Reads `learned_kb` after learning | Receives pre-reduced KB |
| **Mutation semantics** | "Build KB as you learn" | "Compute KB from inputs" |

---

## 6. Feature Immutability Analysis

### Fields That Are Immutable Input

In **QuAcqTask**, these are set once during preparation and never mutated by algorithm:

| Field | Source | Mutability | Algorithm Usage |
|-------|--------|-----------|-----------------|
| `set_b` | Oracle.get_bg_data() | Immutable | Read in conflict resolution |
| `set_kb` | Oracle.get_bg_data() + prepared KB | Immutable | Read for SAT solving |
| `assumptions` | Prepared from KB | Immutable | Read for constraint lookup |
| `negation_map` | Prepared with KB negation | Immutable | Read for REDUCE |
| `feature_ids` | Oracle.get_fm_data() | Immutable | Read for config→assumptions |
| `constraint_clauses` | Built from bias constraints | Immutable | Read for violation checking |
| `negated_clauses` | Built from bias constraints | Immutable | Read by QueryGenerator |
| `background_clauses` | Oracle.get_root_clauses() | Immutable | Read in conflict resolution |

### Fields That Mutate During Learning

| Field | Initial | During Learning | Final State |
|-------|---------|-----------------|------------|
| `learned_kb` | `[]` | Grows via `add_to_kb()` | Contains all learned constraint IDs |
| `bias` | `{c1, c2, ..., cn}` | Shrinks via `remove_from_bias()` | Empty or partial set |
| `query_history` | `[]` | Appends tuples | Full audit trail |
| `n_queries` | `0` | Increments | Total query count |

---

## 7. Key Code Locations

### Task Definition & Initialization
- **File**: `conacq/algorithms/quacq/task_preparation.py`
  - Lines 28-54: `QuAcqTask` dataclass definition
  - Lines 195-262: `QuAcqTaskPreparation.prepare()` — creates and initializes task

### Algorithm Mutations
- **File**: `conacq/algorithms/quacq/quacq.py`
  - Lines 161-220: `QuAcq.learn()` — oracle-based mutations
  - Lines 224-345: `QuAcq.learn_from_examples()` — example-based mutations
  - Lines 395-421: `QuAcq._apply_reduce()` — reads learned_kb

### Task Mutation Methods
- **File**: `conacq/algorithms/quacq/task_preparation.py`
  - Lines 84-87: `QuAcqTask.add_to_kb()` — mutation
  - Lines 89-91: `QuAcqTask.remove_from_bias()` — mutation
  - Lines 93-97: `QuAcqTask.record_query()` — mutation
  - Lines 77-82: `QuAcqTask.get_kb_clauses()` — read from learned_kb

### Runner / Task Creation
- **File**: `conacq/runners/quacq_runner.py`
  - Lines 145-166: `QuAcqRunner.run()` creates fresh model+task per invocation
  - Lines 153-160: Builder pattern ensures task isolation

---

## 8. Algorithm Execution Walkthrough

### Example: QuAcq.learn() with learned_kb Mutations

```python
# Initial state
task.bias = {c1, c2, c3, c4}
task.learned_kb = []

# Query 1: Oracle says "false" (negative example)
conflict = _find_conflict(task, query)  # Returns [c2, c4]
task.add_to_kb(c2)                      # learned_kb = [c2]
task.remove_from_bias([c2])             # bias = {c1, c3, c4}
task.add_to_kb(c4)                      # learned_kb = [c2, c4]
task.remove_from_bias([c4])             # bias = {c1, c3}
task.record_query(config, False)

# Query 2: Oracle says "true" (positive example)
_prune_rejecting_constraints(task, query)  # bias = {c1}  [pruned c3]
task.record_query(config, True)

# Query 3: Oracle says "false"
conflict = _find_conflict(task, query)  # Returns [c1]
task.add_to_kb(c1)                      # learned_kb = [c2, c4, c1]
task.remove_from_bias([c1])             # bias = {}

# Loop exits: bias is empty, convergence_reason = 'empty_bias'

# Final processing
result = _build_result(task, ...)
final_kb = _apply_reduce(task)  # Reads task.learned_kb = [c2, c4, c1]
                               # Returns filtered: [c2, c4, c1]
```

---

## 9. Unresolved Questions

1. **Why does QuAcq mutate task.bias directly?**
   - Answer: Allows O(1) removal via set operations (bias is Set[int])
   - ConGen doesn't need this (batch algorithm)

2. **Could learned_kb be immutable (returned as new list)?**
   - Answer: Technically yes, but would require API change
   - Current design follows interactive learning paradigm (incremental updates)
   - REDUCE reads final state, so immutability of learned_kb isn't critical

3. **Why does QuAcqTask inherit from DiagnosisTask but only uses some fields?**
   - Answer: Inheritance provides common structure for task preparation
   - set_c is unused (always empty) — left for conceptual clarity
   - Allows REDUCE to work uniformly across task types

4. **Is there a race condition if two QuAcq instances share a task?**
   - Answer: Yes, but prevented by runner design (fresh task per run)
   - No synchronization needed if tasks are isolated per algorithm instance

---

## Summary Table: Mutation Patterns

| Operation | Called By | Mutates | Safety |
|-----------|-----------|---------|--------|
| `add_to_kb(c_id)` | QuAcq.learn, learn_from_examples | learned_kb | Safe (single-threaded, ordered) |
| `remove_from_bias(ids)` | QuAcq.learn, learn_from_examples | bias | Safe (set subtraction) |
| `record_query(cfg, ans)` | QuAcq.learn, learn_from_examples | query_history, n_queries | Safe (append, increment) |
| `_apply_reduce(task)` | QuAcq._build_result | — | Reads learned_kb (no mutation) |
| `_find_conflict(task, ex)` | QuAcq.learn, learn_from_examples | — | Returns new list (no mutation) |
| `_prune_rejecting_constraints(task, ex)` | QuAcq.learn, learn_from_examples | bias (via helper) | Safe |

