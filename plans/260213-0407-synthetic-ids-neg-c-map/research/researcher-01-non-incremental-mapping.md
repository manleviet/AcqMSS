# Research: Non-Incremental Mode with neg_c_map

## Q1: NonIncrementalPySATChecker.is_consistent() Input Format

**Answer**: Expects **list of lists** (CNF clauses), NOT clause IDs.

**Implementation** (checker.py, lines 269-280):
```python
def is_consistent(self, set_c: List) -> bool:
    # Flatten set_c from list of lists to single list of clauses
    cnf = [clause for c in set_c for clause in c]
    solver = Solver(self.solver_name, bootstrap_with=cnf, use_timer=True)
    self.result = solver.solve()
    solver.delete()
    return self.result
```

**Data flow**:
- Input: `set_c = [[[1, 2], [-3, 4]], [[5], [-6, 7]]]` (each element is a constraint's clause list)
- Flattened: `[[1, 2], [-3, 4], [5], [-6, 7]]` (flat CNF to solver)
- Each constraint is a list of clauses; multiple constraints are combined via flattening

---

## Q2: Reduce Algorithm neg_c_map Lookup (acqmss/algorithms/reduce.py)

**Lookup mechanism** (lines 104-127):

```python
for c in kb:
    if c not in kb_delta: continue
    kb_without_c = diff(kb_delta, [c])

    # Get ¬c - Convert clause list → name via name_lookup
    if isinstance(c, list) and name_lookup is not None:
        c_key = _to_hashable(c)
        c_key = name_lookup.get(c_key, c_key)
    elif isinstance(c, list):
        c_key = _to_hashable(c)
    else:
        c_key = c

    if c_key not in neg_map: continue
    neg_c = neg_map[c_key]

    # Check: consistent(BG ∪ (KB - {c}) ∪ {¬c})
    test_set = set_bg + kb_without_c + [neg_c]
    is_consistent = self.checker.is_consistent(test_set)
```

**Key points**:
- `c` = clause list (e.g., `[[1, 2], [-3, 4]]`)
- `c_key` = hashcode via `_to_hashable(c)` (converts to hashable tuple) or name from `name_lookup`
- `neg_c` = clause list retrieved from `neg_map[c_key]`
- `test_set` = flat list combining: `set_bg` (clause lists) + `kb_without_c` (clause lists) + `[neg_c]` (single clause list)
- Passed to `is_consistent()` which flattens all clause lists together

---

## Q3: WipeOutR_FM neg_c_map Lookup (explanation/operations/algorithms/wipeoutr_fm.py)

**Lookup mechanism** (lines 59-78):

```python
for c_alpha in set_c:
    if c_alpha not in c_delta: continue
    cf_without_alpha = diff(c_delta, [c_alpha])

    # Get ¬cα
    c_alpha_key = str(c_alpha) if isinstance(c_alpha, List) else c_alpha
    if c_alpha_key not in neg_c_map: continue
    neg_alpha = neg_c_map[c_alpha_key]

    # Check: consistent(CF_Δ - {cα} ∪ {¬cα})
    test_set = cf_without_alpha + [neg_alpha]
    is_consistent = self.checker.is_consistent(test_set)
```

**Key points**:
- `c_alpha` = assumption ID (integer) in incremental mode
- `c_alpha_key` = string representation `str(c_alpha)` (converts int to string key)
- `neg_alpha` = negated assumption ID retrieved from `neg_c_map[c_alpha_key]`
- `test_set` = list of assumption IDs
- Passed to incremental checker which uses assumptions

**Critical difference from Reduce**: WipeOutR_FM works in **incremental mode**, so:
- `set_c` = assumption IDs (integers)
- `neg_c_map` = `Dict[str, int]` mapping (e.g., `{"1": 2, "3": 4}`)
- Checker expects assumption IDs, not clause lists

---

## Q4: NonIncrementalTestCaseTaskPreparation.neg_c_map Generation

**Location** (task_preparation.py, lines 1050-1100):

```python
class NonIncrementalTestCaseTaskPreparation:
    def prepare(self, model):
        result = NonIncrementalTestCaseTask()
        for testcase in testsuite.testcases:
            # Original form: conjunction as list of unit clauses
            original_clauses = [[lit] for lit in literals]
            result.set_kb.append(original_clauses)

            # Negated form: ¬(l1 ∧ l2 ∧ ... ∧ ln) = (¬l1 ∨ ¬l2 ∨ ... ∨ ¬ln)
            negated_clauses = [[-lit for lit in literals]]
            result.set_kb.append(negated_clauses)

            # Map original to negated
            result.neg_tc_map[get_hashcode(original_clauses)] = negated_clauses
```

**Key mechanic** (lines 1070-1073):
- `get_hashcode()` = `str(sorted(clauses))` converts clause list → string key
- Example: `get_hashcode([[1], [2]]) = "[[1], [2]]"`
- Maps: `Dict[str, List[List[int]]]`
- Each test case: `neg_tc_map[hash_of_original] = negated_clauses`

**For redundancy** (lines 912-925 in NonIncrementalDiagnosisTaskPreparation):
```python
for key, clauses in model.constraint_map.items():
    result.set_kb.append(clauses)
    if negated_constraint_map is not None:
        negated_key = f"NOT({key})"
        if negated_key in negated_constraint_map:
            neg_clauses = negated_constraint_map[negated_key]
            result.set_kb.append(neg_clauses)
            result.neg_c_map[get_hashcode(clauses)] = neg_clauses
```

Maps: `Dict[str, List[List[int]]]`
- Key = hashcode of constraint's clause list
- Value = negated constraint's clause list

---

## Q5: DiagnosisModel.get_neg_c_map()

**Location** (pysat_diagnosis_model.py, lines 140-155):

```python
def get_neg_c_map(self) -> dict:
    """Get the mapping from constraint to negated constraint IDs.

    Returns:
        Dict mapping original constraint ID to negated constraint ID,
        or empty dict if no negated forms.
    """
    if self._task is not None:
        return self._task.neg_c_map
    return {}
```

**Task-dependent returns**:
- **Incremental mode**: `Dict[int, int]` (assumption ID → negated assumption ID)
  - Example: `{1: 2, 3: 4}` (constraint ID 1 negated is ID 2)
  - Set in `IncrementalKBPreparator.prepare_kb()` (task_preparation.py, lines 328-330)

- **Non-incremental mode**: `Dict[str, List[List[int]]]` (hashcode → clause list)
  - Example: `{"[[1], [2]]": [[-1, -2]]}`
  - Set in `NonIncrementalDiagnosisTaskPreparation.prepare()` (lines 920-925)

**Field source**: `neg_c_map` defined in `DiagnosisTask` base class (task_preparation.py, line 131):
```python
@dataclass
class DiagnosisTask(ABC):
    neg_c_map: Dict = field(default_factory=dict)
```

---

## Summary: Data Types by Mode

| Aspect | Incremental | Non-Incremental |
|--------|-------------|-----------------|
| **set_c** | `List[int]` (assumption IDs) | `List[List[List[int]]]` (clause lists) |
| **neg_c_map key** | `int` → `int` | `str` (hashcode) → `List[List[int]]` (clause list) |
| **neg_c_map lookup** | Direct ID mapping | Hashcode via `get_hashcode()` → clause list |
| **is_consistent() input** | `List[int]` (assumptions) | `List[List[List[int]]]` (clause lists) |
| **Checker** | IncrementalPySATChecker | NonIncrementalPySATChecker |

---

## Critical Findings

1. **Non-incremental neg_c_map requires get_hashcode()**
   - Always use `get_hashcode(clauses)` for dict keys (converts list to string)
   - `_to_hashable()` in Reduce (line 116) does tuple conversion; verify compatibility

2. **WipeOutR_FM inconsistency**: Uses `str(c_alpha)` instead of `get_hashcode()`
   - Works only if keys are IDs, fails with clause lists
   - Need synthetic ID mapping to fix

3. **Reduce uses optional name_lookup**
   - Can override hashcode → name mapping for debugging output
   - Not used in core logic, only in description providers

4. **NonIncrementalTestCaseTaskPreparation populates neg_tc_map similarly**
   - Pattern: `neg_tc_map[get_hashcode(original)] = negated_clauses`
   - Both use clause list hashes, consistent pattern

---

## Unresolved Questions

1. Why does WipeOutR_FM use `str(c_alpha)` vs `get_hashcode()`? Is it buggy for non-incremental?
2. What synthetic ID format would best bridge incremental and non-incremental modes?
3. Should name_lookup be propagated to WipeOutR_FM for non-incremental debugging?
