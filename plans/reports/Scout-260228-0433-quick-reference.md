# Quick Reference: Assignment-to-Assumption Dicts

## Core Files at a Glance

| File | Key Roles |
|------|-----------|
| `conacq/oracle/fm_oracle_model.py` | **Creation** (lines 206-231), Storage in FMOracleModel (lines 48-49, 230-231) |
| `conacq/oracle/bg_data.py` | **Propagation** (lines 38-39): Dataclass fields |
| `conacq/oracle/fm_oracle.py` | **Extraction** (lines 103-105): `get_bg_data()` method |
| `conacq/algorithms/quacq/task_preparation.py` | **Copy to QuAcqTask** (lines 106-107), Field definitions (lines 65-66) |
| `conacq/algorithms/quacq/quacq.py` | **Primary consumption** (lines 109-110, 204-208, 311-313) |
| `conacq/runners/quacq_runner.py` | **Parameter extraction** (lines 62-63) |
| `tests/test_quacq.py` | **Test usage** (lines 54-55, 668-669, 779-783, 804-809) |

---

## Trace: From Creation to Consumption

### 1. Creation
```
FMOracleTaskPreparation.prepare()
  ├─ for each feature in model.variables:
  │  ├─ pos_assignment_to_assumption[feat] = a_pos_id
  │  └─ neg_assignment_to_assumption[feat] = a_neg_id
  └─ Lines 206-231 in fm_oracle_model.py
```

### 2. Storage
```
FMOracleModel._pos_assignment_to_assumption = dict    (line 230)
FMOracleModel._neg_assignment_to_assumption = dict    (line 231)
↓
BGData.pos_assignment_to_assumption = dict(...)       (line 257)
BGData.neg_assignment_to_assumption = dict(...)       (line 258)
```

### 3. Extraction
```
FeatureModelOracle.get_bg_data()  →  BGData with dicts  (fm_oracle.py:103-105)
```

### 4. Propagation
```
QuAcqTaskPreparation.prepare()
  └─ result.pos_assignment_to_assumption = dict(bg_data.pos_assignment_to_assumption)  (line 106)
  └─ result.neg_assignment_to_assumption = dict(bg_data.neg_assignment_to_assumption)  (line 107)
```

### 5. Parameter Passing
```
QuAcqTask → _learn_params_from_task() → QuAcq.learn()
             (quacq_runner.py:51-65)   (quacq.py:109-110)
```

### 6. Consumption
```
QuAcq._prune_rejecting_constraints()
  └─ config_assumptions = [pos_map[f] if v else neg_map[f] for f,v in example.items()]
     (quacq.py:311-313)
```

---

## Key Methods

### Creation Loop (FMOracleTaskPreparation.prepare)
```python
pos_assignment_to_assumption = {}
neg_assignment_to_assumption = {}

for name, fid in model.variables.items():
    a_pos = id_assumption++
    a_neg = id_assumption++
    pos_assignment_to_assumption[name] = a_pos
    neg_assignment_to_assumption[name] = a_neg
    result.set_kb.append([-a_pos, fid])
    result.set_kb.append([-a_neg, -fid])
```

### Conversion Logic (QuAcq._prune_rejecting_constraints)
```python
config_assumptions = [
    pos_map[feat] if val else neg_map[feat]
    for feat, val in positive_example.items()
    if feat in pos_map
]
base = [root_assumption] + config_assumptions
for aid in remaining_bias:
    if not checker.is_consistent(base + [aid]):
        pruned.append(aid)
```

### Alternative Conversion (FMOracleModel._config_to_assumptions)
```python
return [
    self._pos_assignment_to_assumption[feat] if value 
    else self._neg_assignment_to_assumption[feat]
    for feat, value in configuration.items()
]
```

---

## Data Structures

### Dictionaries
```python
pos_assignment_to_assumption: Dict[str, int]
  # Example: {'root': 210, 'f1': 212, 'f2': 214}
  # Meaning: if feature is TRUE, use this assumption ID

neg_assignment_to_assumption: Dict[str, int]
  # Example: {'root': 211, 'f1': 213, 'f2': 215}
  # Meaning: if feature is FALSE, use this assumption ID
```

### Storage Locations
1. **FMOracleModel instance variables:**
   - `_pos_assignment_to_assumption`: Dict[str, int]
   - `_neg_assignment_to_assumption`: Dict[str, int]

2. **BGData immutable fields:**
   - `pos_assignment_to_assumption`: Dict[str, int]
   - `neg_assignment_to_assumption`: Dict[str, int]

3. **QuAcqTask dataclass fields:**
   - `pos_assignment_to_assumption`: Dict[str, int]
   - `neg_assignment_to_assumption`: Dict[str, int]

4. **QuAcq.learn() parameters:**
   - `pos_assignment_to_assumption: Dict[str, int] = None`
   - `neg_assignment_to_assumption: Dict[str, int] = None`

---

## Important Notes

### Optional Feature
- Dicts are optional in `QuAcq.learn()` (default to None)
- If None, QuAcq falls back to legacy Boolean evaluation

### Part 4 of Assumption ID Layout
- Part 1-2: Feature variables + Tseitin (Oracle)
- Part 3: FM constraint assumptions (Oracle)
- **Part 4: Feature assignment assumptions** ← Assignment dicts here
- Part 5-6: Negated bias + bias constraint assumptions (QuAcq)

### Unit Clauses Generated
For each feature `f` with ID `fid`:
- `[-a_pos, fid]`: If a_pos active, f must be true
- `[-a_neg, -fid]`: If a_neg active, f must be false

### Test Examples
- Line 804-809 in test_quacq.py: Assert dicts contain all features
- Line 50-51 in test_oracle_model.py: Direct assumption ID lookup

---

## Inheritance Chain

```
DiagnosisTask (parent)
    ↓
QuAcqTask (child)
    ├─ Inherited fields: set_c, set_b, set_kb, negation_map, assumptions
    └─ Added fields: background_clauses, feature_ids, id_to_feature,
                     constraint_clauses, negated_clauses,
                     assignment_clauses, assignment_assumptions,
                     pos_assignment_to_assumption,     ← Part 4
                     neg_assignment_to_assumption      ← Part 4
```

---

## Summary

**What:** Two dictionaries mapping feature names to assumption IDs
**Why:** SAT-based pruning in QuAcq uses assumption-guarded unit clauses
**Where:** Created in Oracle, propagated through BGData, stored in QuAcqTask
**How:** For each feature, create pos/neg pair of assumption IDs and unit clauses
**When:** During FMOracleModel.prepare() at startup

