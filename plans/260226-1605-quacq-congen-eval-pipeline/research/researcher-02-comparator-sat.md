# Researcher 02 — KBComparator & SAT Infrastructure

## KBComparator

**File:** `conacq/eval/kb_comparator.py`

**Inputs:**
- `oracle: GroundTruthData` — ground truth from FM
- `bias: Bias` — all candidate constraints with descriptions/clauses
- `result: ConGenResultData` — what ConGen learned

**Output:** `ComparationResult` dataclass (L28–48):
```python
strategy: str                  # "description" or "clause"
metrics: EvaluationMetrics     # TP, FP, FN (TN=0 for description)
kb_constraints: List[str]      # all KB constraint IDs
matched_constraints: List[str] # TP — IDs matching oracle
missed_constraints: List[str]  # FN — in oracle, not KB (descriptions for desc-strategy)
extra_constraints: List[str]   # FP — in KB, not oracle
kb_reduction_ratio: float      # 1 - (n_kb / n_bias)
```

**Two strategies:**
1. **DESCRIPTION** (L131–186): string-set intersection of `oracle.descriptions` vs KB descriptions via `bias.get_description(cid)`. Skips `ne_*` constraint IDs.
2. **CLAUSE** (L188–242): normalized `tuple(sorted(clause))` set intersection. Also unions `result.bg_clauses` into KB clause set. Calls `compute_metrics(kb_clauses, oracle.clause_set, bias_clauses)`.

**Clause-based metric computation** (`conacq/eval/metrics.py`):
- `TP = kb_clauses ∩ oracle.clause_set`
- `FP = kb_clauses - oracle.clause_set`
- `FN = oracle.clause_set - kb_clauses`

---

## GroundTruthData

**File:** `conacq/oracle/ground_truth.py`

**Fields:**
| Field | Type | Source |
|---|---|---|
| `descriptions` | `Set[str]` | `extract_constraint_descriptions(fm)` |
| `clauses` | `List[List[int]]` | flattened `fm_model.constraint_map.values()` |
| `clause_set` | `Set[Tuple[int,...]]` | `{tuple(sorted(c)) for c in clauses}` |
| `feature_map` | `Dict[str, int]` | `fm_model.variables` |
| `root_feature` | `str` | `fm.root.name` |

**Getting C_T clauses** (L51–53):
```python
fm_model = FmToDiagPysat(fm, create_negation=False).transform()
clauses = [clause for clauses in fm_model.constraint_map.values() for clause in clauses]
clause_set = {tuple(sorted(c)) for c in clauses}  # C_T as normalized set
```
`clause_set` IS C_T — the complete CNF encoding of the FM (root constraint + all feature tree clauses + cross-tree constraints).

**Instantiation:** `GroundTruthData.from_uvl(Path("model.uvl"))` — no oracle or solver needed.

---

## SAT-Based Entailment

**File:** `explanation/operations/algorithms/checker.py`

**Existing interface** — `ConsistencyChecker.is_consistent(set_c: List) -> bool`

The checker already bootstrapped with `set_kb` (background clauses) uses PySAT assumptions to enable/disable constraints. The `_compute_delta` method (L42–46) partitions `set_c` vs remaining assumptions.

**Entailment pattern** — `KB ⊨ φ` iff `KB ∧ ¬φ` is UNSAT:

```python
# KB ⊨ c_t  (does learned KB entail a target clause?)
# Negate c_t: for clause [a, b] → add [-a] and [-b] as unit clauses
def kb_entails_clause(checker, kb_clauses, clause):
    negated = [[-lit] for lit in clause]  # negate each literal
    formula = kb_clauses + negated
    return not checker.is_consistent(formula)  # UNSAT → entailed

# C_T ⊨ KB  (does ground truth entail all KB clauses?)
# For each KB clause c: check if C_T ∧ ¬c is UNSAT
def ct_entails_kb(ct_clauses, kb_clauses):
    from pysat.solvers import Solver
    for clause in kb_clauses:
        negated = [[-lit] for lit in clause]
        with Solver('glucose3', bootstrap_with=ct_clauses + negated) as s:
            if s.solve():  # SAT → C_T does NOT entail this clause
                return False
    return True
```

**Direct construction without CheckerModel** (L91–101):
```python
checker = IncrementalPySATChecker(
    set_kb=bg_clauses + kb_clauses,  # bootstrap formula
    assumptions=[],                   # no assumption variables needed
)
sat = checker.is_consistent([[neg_lit1], [neg_lit2]])  # add negated clause
entailed = not sat
```

**Factory pattern** (L232–245):
```python
checker = CheckerFactory.create_from_model(model)  # uses model.use_incremental
```

**Semantic equivalence** `KB ≡ C_T`:
- `KB ⊨ C_T` AND `C_T ⊨ KB` → both directions must hold

---

## ConGenResultData

**File:** `conacq/eval/result_loader.py`

**Fields:**
| Field | Type | JSON key |
|---|---|---|
| `kb_constraints` | `List[str]` | `kb_constraints` (IDs or `[{id, description}]`) |
| `redundant_constraints` | `List[str]` | `redundant_constraints` |
| `n_bias` | `int` | `statistics.n_bias` |
| `n_mss` | `int` | `statistics.n_mss` |
| `n_kb` | `int` | `statistics.n_kb` |
| `bg_clauses` | `List[List[int]]` | `bg_clauses` (e.g., `[[1]]` for root) |
| `metadata` | `Dict` | `metadata` |

**Two constructors:**
- `ConGenResultData.from_json(path)` — from result JSON file (L59–83)
- `ConGenResultData.from_dict(data)` — from in-memory dict (fold data in unified JSON, L36–56); handles both `List[str]` and `List[{id,description}]` formats

---

## ConGenModel.resolve_result

**File:** `conacq/algorithms/acqmss/congen_model.py` (L192–204)

```python
def resolve_result(self, result: ConGenResult):
    bg_clauses = self._root_constraint or []
    kb_clauses, kb_names = self._resolve_ids(result.kb_assumption_ids)
    _, redundant_names = self._resolve_ids(result.redundant_ids)
    return bg_clauses, kb_clauses, kb_names, redundant_names
```

`_resolve_ids` (L173–190): maps assumption integer IDs → constraint names via `description_provider`, then looks up CNF clauses from `constraint_map`. This bridges internal ConGen assumption integers back to human-readable constraint IDs and their clauses.

---

## Key Locations Summary

| Component | File | Lines |
|---|---|---|
| `ComparationResult` | `conacq/eval/kb_comparator.py` | 28–59 |
| `KBComparator.compare()` | `conacq/eval/kb_comparator.py` | 108–129 |
| `_compare_by_description` | `conacq/eval/kb_comparator.py` | 131–186 |
| `_compare_by_clause` | `conacq/eval/kb_comparator.py` | 188–242 |
| `GroundTruthData` | `conacq/oracle/ground_truth.py` | 14–71 |
| `GroundTruthData.from_uvl()` | `conacq/oracle/ground_truth.py` | 31–63 |
| `ConsistencyChecker.is_consistent()` | `explanation/operations/algorithms/checker.py` | 49–51 |
| `IncrementalPySATChecker` | `explanation/operations/algorithms/checker.py` | 91–134 |
| `CheckerFactory` | `explanation/operations/algorithms/checker.py` | 220–245 |
| `ConGenResultData` | `conacq/eval/result_loader.py` | 14–111 |
| `ConGenModel.resolve_result()` | `conacq/algorithms/acqmss/congen_model.py` | 192–204 |

---

## Unresolved Questions

1. `compute_metrics()` in `conacq/eval/metrics.py` — exact TN calculation not verified; description strategy always sets TN=0 (L158–163), clause strategy may differ.
2. For SAT-based entailment (`KB ⊨ C_T`), whether to check clause-by-clause or whole formula equivalence — clause-by-clause is standard but may be slow for large C_T.
3. `bg_clauses` in `ConGenResultData` are included in clause-based comparison (L210–213) but NOT in description-based. If building SAT entailment checker, must decide whether to include bg_clauses in the KB formula.
4. `ne_*` constraints are skipped in both strategies (L147, L199) — confirm this is correct for entailment checks too.
