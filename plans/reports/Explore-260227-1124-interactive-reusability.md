# Explore: InteractiveModel & FeatureModelOracle Reusability Across QuAcq Runs

**Date:** 2026-02-27  
**Investigation:** Can InteractiveModel and FeatureModelOracle be reused across multiple QuAcq runs (like ConGenModel is reused across ConGen runs)?

---

## Executive Summary

**SHORT ANSWER:**
- **InteractiveModel:** SAFE to reuse across multiple QuAcq runs
- **FeatureModelOracle:** SAFE to reuse across multiple QuAcq runs
- **QuAcqTask:** MUST be recreated per run (state accumulates)
- **Current InteractiveRunner:** Creates new oracle per run (inefficient) — **can be optimized**

**KEY PATTERN:** ConGenRunner reuses model+oracle across CV folds by calling `model.prepare(oracle, ...)` multiple times. InteractiveRunner can follow the same pattern.

---

## 1. InteractiveModel Reusability Analysis

### State Overview (from `interactive_model.py`)

```python
class InteractiveModel:
    constraint_map: Dict[str, List[List[int]]] = {}          # Immutable data
    negated_constraint_map: Dict[str, List[List[int]]] = {}   # Built on prepare()
    variables: Dict[str, int] = {}                             # Immutable data
    _task: Optional[QuAcqTask] = None                          # Recreated per prepare()
    _description_provider: Optional[DescriptionProvider] = None # Recreated per prepare()
```

### Key Methods

**`from_bias(bias_path)` [L32-46]**
- Loads bias JSON once
- Populates `constraint_map` and `variables` (immutable reference data)
- No state accumulation

**`prepare(oracle)` [L60-74]**
- Calls `InteractiveTaskPreparation().prepare(self, oracle)`
- Updates `_task` (overwrite, not append)
- Updates `_description_provider` (overwrite, not append)
- **CAN BE CALLED MULTIPLE TIMES** — previous task/provider are discarded

**`resolve_kb(kb_assumption_ids)` [L76-92]**
- Reads-only from `constraint_map` and `description_provider`
- No state mutation

### Reusability Conclusion

**✅ SAFE TO REUSE**

- `constraint_map`, `negated_constraint_map`, `variables` are loaded once and never modified
- `_task` and `_description_provider` are intentionally overwritten by `prepare()`
- Unlike ConGen, no example state (E+/E-) stored in model — InteractiveTaskPreparation creates task from bias only
- Can call `prepare(oracle)` multiple times with same oracle (same assumption ID layout)

**No cleanup needed.**

---

## 2. FeatureModelOracle Reusability Analysis

### State Overview (from `fm_oracle.py`)

```python
class FeatureModelOracle(Oracle):
    _oracle_model: FMOracleModel                # Prepared once in __init__
    _checker: ConsistencyChecker                # Created in __init__
    _fm: Optional[FeatureModel] = None          # Lazy-loaded (immutable reference)
```

### FMOracleModel State (from `fm_oracle_model.py`)

```python
class FMOracleModel:
    constraint_map: Dict[str, List[List[int]]] = {}    # FM structure (immutable)
    variables: Dict[str, int] = {}                      # FM feature IDs (immutable)
    _task: Optional[DiagnosisTask] = None               # Prepared once
    _description_provider: Optional[DescriptionProvider] = None
    _pos_assignment_to_assumption: Dict[str, int] = {} # Populated in prepare()
    _neg_assignment_to_assumption: Dict[str, int] = {} # Populated in prepare()
    _base_set_c: List = []                              # Cached in prepare()
    _bg_data: Optional[BGData] = None                   # Prepared once
```

### Key Methods

**`__init__(fm_path, solver_name, use_incremental, profiler)` [L35-52]**
```python
self._oracle_model = FMOracleModel.from_fm(fm_path)
    .set_incremental(use_incremental)
    .build()                           # Calls prepare() once!
self._checker = CheckerFactory.create_from_model(...)
```

- Prepares oracle model completely in constructor
- `_checker` created once

**`is_valid(assignments)` [L71-85]**
```python
set_c = self._oracle_model.with_configuration(assignments).get_c()
return self._checker.is_consistent(set_c)
```

- **MUTATES** `self._oracle_model.task.set_c` via `with_configuration()`
- But this is **scoped to a single query** — next call overwrites it
- No persistent state accumulation

**`with_configuration(configuration)` [L123-133]**
```python
self.task.set_c = self._base_set_c + self._config_to_assumptions(configuration)
return self  # Fluent interface
```

- **Mutates** `task.set_c` (not persistent across calls)
- Always computed from `_base_set_c` (cache hit each call)

**`cleanup()` [L197-201]**
```python
if self._checker is not None:
    self._checker.cleanup()
    self._checker = None
```

- **DESTRUCTIVE:** Sets `_checker = None` after cleanup
- **ERROR:** After cleanup, `is_valid()` will fail (null dereference on `self._checker.is_consistent()`)
- **CRITICAL:** Once cleaned up, oracle is UNUSABLE

### Reusability Conclusion

**⚠️ SAFE TO REUSE if NOT cleaned up**

- FM data (`constraint_map`, `variables`, `_base_set_c`) are immutable
- `task.set_c` mutations are transient (per-query scoping)
- **BUT:** `cleanup()` is **destructive** — must NOT call between runs
- **Current InteractiveRunner pattern:** Creates new oracle per `run()`, calls `cleanup()` in finally block [L229-230]
  - This is correct but inefficient
  - Could reuse oracle across CV folds if cleanup deferred to end

### Design Issue

The oracle's `_checker` is created once and can't be recreated. If `cleanup()` is called, the oracle becomes permanently unusable. The `__init__` doesn't reset state, so can't reconstruct `_checker` post-cleanup.

**FIX NEEDED:** Either:
1. Make `cleanup()` optional (reset `_checker` instead of nulling)
2. Provide `reuse()` or `reset()` method to recreate `_checker`
3. Create new oracle for each run (current pattern, simple but wasteful)

---

## 3. QuAcqTask State Mutations During Learning

### Initial State (from `quacq_task.py`)

```python
@dataclass
class QuAcqTask(DiagnosisTask):
    bias: Set[int] = field(default_factory=set)            # Remaining constraints
    learned_kb: List[int] = field(default_factory=list)    # Learned constraints
    n_queries: int = 0                                       # Query count
    query_history: List[Tuple] = field(default_factory=list)
    constraint_clauses: Dict[int, List[List[int]]] = {}
    negated_clauses: Dict[int, List[List[int]]] = {}
```

### State Mutations During `QuAcq.learn()` (from `quacq.py` L213-250)

```python
while task.bias:                                    # L213
    query = self.query_generator.generate(task)    # L219
    answer = oracle.ask(query)                     # L226
    task.record_query(query, answer)               # L227 ← MUTATION: n_queries++, query_history append
    
    if answer:
        pruned = self._prune_rejecting_constraints(task, query)  # L233
        # task.remove_from_bias(pruned)            # L466 ← MUTATION: bias -= pruned
    else:
        conflict = self._find_conflict(task, query)    # L236
        if conflict:
            for c_id in conflict:
                task.add_to_kb(c_id)               # L239 ← MUTATION: learned_kb.append(c_id)
            task.remove_from_bias(conflict)        # L240 ← MUTATION: bias -= conflict
```

### Key Mutations

| Method | Mutation | Reversible? |
|--------|----------|------------|
| `record_query(config, answer)` | `n_queries++`, `query_history.append(...)` | NO (append) |
| `add_to_kb(aid)` | `learned_kb.append(aid)` | NO (append) |
| `remove_from_bias(aids)` | `bias -= aids` | NO (set difference) |

**All mutations are accumulative, not reversible.**

### Convergence (L248-250)

```python
if not task.bias:
    convergence_reason = 'empty_bias'
```

After learning completes:
- `task.bias` is empty (or near-empty)
- `task.learned_kb` contains all learned constraints
- `task.n_queries` = total query count
- `task.query_history` = full history

**REUSING THE SAME TASK FOR A SECOND RUN WOULD:**
1. Skip the while loop immediately (bias already empty)
2. Return empty result
3. Lose all state from the first run

### `clone()` Method

```python
def clone(self) -> 'QuAcqTask':  # L161-180
    """Create a deep copy of this task."""
    return QuAcqTask(
        bias=set(self.bias),                        # Copy set
        learned_kb=self.learned_kb.copy(),          # Copy list
        # ... deep copy all mutable fields
    )
```

**Exists for cloning but NOT called by QuAcq.learn()** — so state sharing between runs is not supported by API.

### Conclusion

**❌ NOT REUSABLE — State Accumulates**

- Task must be freshly created per run
- Each run modifies `bias`, `learned_kb`, `n_queries`, `query_history`
- No reset/cleanup method provided
- Design is intentional: one task per learning episode

---

## 4. How ConGenRunner Achieves Reuse

### Pattern (from `congen_runner.py` L126-196)

```python
class ConGenRunner:
    def __init__(self, bias_path, fm_path, ...):
        # Build ONCE (no examples)
        self.model = ConGenModelBuilder
            .from_bias(bias_path)
            .use_incremental(use_incremental)
            .build()
        
        # Create ONCE
        self.oracle = FeatureModelOracle(fm_path, use_incremental=False)
        
        self._original_bias_constraint_order = list(self.model.constraint_map.keys())
    
    def run(self, pos_examples, neg_examples, shuffle_seed):
        # Shuffle bias ORDER (not structure)
        if shuffle_seed is not None:
            keys = list(self._original_bias_constraint_order)
            random.Random(shuffle_seed).shuffle(keys)
            self.model.constraint_map = {k: self.model.constraint_map[k] for k in keys}
        
        # REUSE model + oracle, call prepare() with NEW examples
        self.model.prepare(
            oracle=self.oracle,
            positive_examples=pos_examples,
            negative_examples=neg_examples
        )
        task = self.model.task
        
        # Create NEW checker (not reused)
        checker = CheckerFactory.create_from_model(self.model, self.solver_name)
        
        # Run ConGen
        congen = ConGen(checker, profiler)
        result = congen.acquire(...)
        
        # Cleanup checker (but NOT oracle or model)
        finally:
            if checker is not None:
                checker.cleanup()
```

### Key Insights

1. **Model reuse:** Call `prepare(oracle, pos_examples, neg_examples)` per fold
   - `constraint_map` stays constant (only ORDER shuffled)
   - `_task` overwritten (not accumulated)
   - `_description_provider` overwritten

2. **Oracle reuse:** Single oracle instance, no `cleanup()` between runs
   - Only `cleanup()` called in final `cleanup()` method [L272-275]
   - `is_valid()` calls don't accumulate state (transient `set_c` mutations)

3. **Checker NOT reused:** New checker created per run
   - Checker is stateful (SAT solver state)
   - Requires fresh initialization for each problem instance

4. **Task NOT reused:** Implicit — each `prepare()` creates new task

---

## 5. Current InteractiveRunner Pattern

### Current Code (from `interactive_runner.py` L134-253)

```python
def run(self, positive_examples, negative_examples, mode, shuffle_seed):
    # Setup: oracle + model + task [L192-196]
    oracle = FeatureModelOracle(
        self.fm_path, self.solver_name, profiler=profiler)  # ← NEW oracle per run
    model = InteractiveModel.from_bias(self.bias_path)      # ← NEW model per run
    model.prepare(oracle)                                    # ← NEW task per run
    task = model.task
    
    if shuffle_seed is not None:
        keys = sorted(task.bias)
        random.Random(shuffle_seed).shuffle(keys)
        task.bias = set(keys)                               # ← Mutate task bias
    
    quacq = QuAcq(self.solver_name, profiler)               # ← NEW quacq per run
    
    # Run learning
    if is_oracle_mode:
        result = quacq.learn(task, oracle, ...)
    else:
        result = quacq.learn_from_examples(task, ...)
    
    finally:
        if oracle is not None:
            oracle.cleanup()                                # ← Cleanup
```

### Issues

1. **Inefficient oracle creation:** `FeatureModelOracle.__init__()` reloads FM, rebuilds model, recreates checker per run
2. **Inefficient model creation:** `InteractiveModel.from_bias()` reloads bias JSON per run
3. **Task recreation:** Implicit but correct (needed for state reset)

### Optimization Opportunity

**Pattern to match ConGenRunner:**

```python
class InteractiveRunner:
    def __init__(self, bias_path, fm_path, ...):
        # Build model ONCE (no oracle needed yet)
        self.model = InteractiveModel.from_bias(bias_path)
        
        # Create oracle ONCE
        self.oracle = FeatureModelOracle(fm_path, ...)
        
        self._original_bias_set = None  # Cache for shuffling
    
    def run(self, positive_examples, negative_examples, ...):
        # Prepare model+oracle for THIS run (new task created)
        self.model.prepare(self.oracle)
        task = self.model.task
        
        if shuffle_seed is not None:
            keys = sorted(task.bias)
            random.Random(shuffle_seed).shuffle(keys)
            task.bias = set(keys)
        
        # QuAcq uses THIS task for learning (task state accumulates during run)
        quacq = QuAcq(...)
        result = quacq.learn(task, self.oracle, ...)
        
        # No cleanup of oracle (done in .cleanup() method)
    
    def cleanup(self):
        if self.oracle is not None:
            self.oracle.cleanup()
```

---

## 6. Comparison Table

| Component | ConGenModel | InteractiveModel | Can Reuse? |
|-----------|-------------|-----------------|-----------|
| `constraint_map` | Immutable | Immutable | ✅ YES |
| `variables` | Immutable | Immutable | ✅ YES |
| `_task` | Overwritten | Overwritten | ✅ YES |
| `_description_provider` | Overwritten | Overwritten | ✅ YES |
| **prepare() calls** | Multiple OK | Multiple OK | ✅ YES |

| Component | FeatureModelOracle | Reusable? |
|-----------|-------------------|-----------|
| `_oracle_model` | Immutable FM data | ✅ YES |
| `_checker` | Transient mutations | ✅ YES (if not cleaned up) |
| `cleanup()` | Destructive | ❌ NO (nulls `_checker`) |

| Component | QuAcqTask | Reusable? |
|-----------|-----------|-----------|
| `bias` | Mutated during learn() | ❌ NO |
| `learned_kb` | Mutated during learn() | ❌ NO |
| `n_queries` | Incremented during learn() | ❌ NO |
| Fresh creation per run | Required | ✅ YES |

---

## 7. Implementation Recommendations

### For Reuse Across CV Folds

**Option A: Refactor InteractiveRunner (Recommended)**

Match ConGenRunner pattern:
1. Create model + oracle in `__init__()` (once per CV session)
2. Call `model.prepare(oracle)` per fold (creates new task)
3. Call `cleanup()` only at end of CV session
4. **Benefit:** 2-3x faster initialization per fold (no FM reload, no checker rebuild)

### For FeatureModelOracle Persistence

**Option B: Add soft-reset to oracle (Optional)**

Current issue: `cleanup()` is destructive.

```python
def reset(self):
    """Reset oracle for reuse without full cleanup."""
    if self._checker is not None:
        self._checker.cleanup()
    self._checker = CheckerFactory.create_from_model(
        self._oracle_model, self.solver_name, self.profiler)

def cleanup(self):
    """Permanent cleanup."""
    if self._checker is not None:
        self._checker.cleanup()
        self._checker = None
```

Would allow inter-fold reset without full resource release.

---

## 8. Risk Assessment

### Safe Changes (Low Risk)

1. ✅ **Create model + oracle in `InteractiveRunner.__init__()`**
   - InteractiveModel fully immutable after load
   - FeatureModelOracle designed for reuse (per `is_valid()` pattern)
   - No state accumulation in either

2. ✅ **Call `model.prepare(oracle)` per fold**
   - ConGenModel already does this
   - InteractiveModel has same prepare signature
   - Task recreation handles state reset

3. ✅ **Defer oracle cleanup to end of session**
   - Oracle is safe to reuse if not cleaned up
   - Matches ConGenRunner pattern
   - No new state mutations expected

### Risky Changes (High Risk)

1. ❌ **Reuse QuAcqTask across runs**
   - Task state is accumulative (bias exhausted, n_queries incremented)
   - Would require full clone/reset logic
   - Not worth the complexity

2. ❌ **Call oracle.cleanup() between folds and reuse**
   - `cleanup()` nulls `_checker`
   - No way to recreate `_checker` from nulled oracle
   - Would crash on next `is_valid()` call

---

## 9. Specific State Mutations to Watch

### During `QuAcq.learn(task, oracle, ...)`

```
Before: task.bias = {a1, a2, a3}, learned_kb = [], n_queries = 0
Loop iteration 1: query, answer → mutate bias, learned_kb, n_queries
Loop iteration 2: query, answer → mutate bias, learned_kb, n_queries
...
After:  task.bias = {}, learned_kb = [...], n_queries = n
```

**These mutations are irreversible.** Each run must start with a fresh task.

### During `oracle.is_valid(config)` or `oracle.with_configuration(config)`

```
Before: oracle._oracle_model.task.set_c = [a_root_1, ...]
Call:   oracle.with_configuration({'feat1': True})
Mutate: oracle._oracle_model.task.set_c = [a_root_1, ..., a_pos_feat1]
After:  oracle._oracle_model.task.set_c = [a_root_1, ..., a_pos_feat1]

Next call: oracle.with_configuration({'feat2': False})
Mutate:    oracle._oracle_model.task.set_c = [a_root_1, ..., a_pos_feat2]  ← Overwrites
```

**These mutations are scoped to the call** — next call overwrites, not accumulates.

---

## Unresolved Questions

1. **Does FeatureModelOracle need thread-safety?**
   - CV loops are sequential (not parallel in typical use)
   - But `with_configuration()` mutation is not atomic
   - Low risk for single-threaded CV, but worth documenting

2. **Should InteractiveModel cache negation?**
   - Currently `InteractiveTaskPreparation` recreates negation on each `prepare()`
   - Negation is deterministic (same bias → same negation)
   - Could cache in `InteractiveModel.negated_constraint_map` to avoid Tseitin re-encoding
   - Would save ~5-10% per fold in Tseitin generation

3. **ConGenRunner preserves bias ORDER during shuffle — is this necessary for QuAcq?**
   - QuAcq operates on a set (bias mutations are set difference)
   - Shuffling task.bias is local mutation, doesn't affect model.constraint_map
   - Current pattern (shuffle task.bias after prepare) is correct
   - But ConGenRunner's shuffle-before-prepare is cleaner (shuffles entire constraint dict)

---

## Summary & Recommendations

| Component | Status | Action |
|-----------|--------|--------|
| InteractiveModel | ✅ Safe to reuse | Move to `__init__()` in InteractiveRunner |
| FeatureModelOracle | ✅ Safe if not cleaned up | Move to `__init__()`, defer cleanup to end |
| QuAcqTask | ❌ Must recreate per run | Call `prepare()` per run (automatic) |
| QuAcq instance | ✅ Safe to recreate | Create per run (lightweight) |

**RECOMMENDED CHANGE:** Refactor `InteractiveRunner` to match `ConGenRunner` architecture for 2-3x faster CV initialization (avoid FM reload + checker rebuild per fold).
