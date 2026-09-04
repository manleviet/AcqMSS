# Exploration Report: Oracle Evaluation, Negation Map, and Root Constraint Handling

**Date**: 2026-02-25 | **Scope**: Comprehensive analysis of constraint evaluation pipeline

---

## 1. How Learned Constraints Are Compared to Oracle Constraints

### Two-Strategy Comparison Framework (`conacq/eval/kb_comparator.py`)

The `KBComparator` class compares learned KB against oracle (ground truth) using **two semantically different strategies**:

#### Strategy 1: Description-Based (Recommended)
- **What**: Compare constraint **human-readable descriptions** (strings)
- **How**: 
  1. Extract FM descriptions from oracle via `extract_constraint_descriptions(fm)`
  2. For each KB constraint ID, get its bias description
  3. Compute metrics: TP = intersection, FP = KB-only, FN = oracle-only
- **When Used**: Primary evaluation method for reporting acquired constraints
- **Example**:
  ```python
  fm_descriptions = self.oracle.descriptions  # {"Allow A if B", "Require C", ...}
  acquired = {self.bias.get_description(cid) for cid in result.kb_constraints}
  tp = acquired & fm_descriptions  # Matched descriptions
  ```

#### Strategy 2: Clause-Based (Semantic)
- **What**: Compare **CNF clauses** (semantic equivalence)
- **How**:
  1. Convert KB constraint IDs → CNF clauses (normalized with sorted tuples)
  2. Union KB clauses with background clauses
  3. Compare clause sets against oracle clause set
- **When Used**: Semantic-level evaluation, handles clause redundancy
- **Key Feature**: Includes `bg_clauses` in the comparison

### The Evaluation Metrics (Formula 1, Paper page 6)

```
TP: Constraint in both KB and oracle
TN: Not applicable (no negative constraint set)
FP: Constraint in KB but NOT in oracle (error)
FN: Constraint in oracle but NOT in KB (missed)

Accuracy = (TP + TN) / (TP + TN + FP + FN)
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 * Precision * Recall / (Precision + Recall)
```

### Accuracy Calculation on Test Examples (`conacq/eval/accuracy.py`)

Separate from constraint comparison, accuracy is measured on **test examples**:
- **Input**: KB clauses + variable mapping + test examples (E⁺ and E⁻)
- **Process**:
  1. For each positive example: Check if accepted by KB (consistency check)
    - TP: Positive example ACCEPTED ✓
    - FN: Positive example REJECTED ✗
  2. For each negative example: Check if rejected by KB
    - TN: Negative example REJECTED ✓
    - FP: Negative example ACCEPTED ✗
- **Output**: AccuracyResult with metrics and per-example classifications

---

## 2. The Negation Map (`negation_map: Dict[int, int]`)

### Purpose and Structure

The **negation_map** is a **bidirectional mapping** from assumption IDs to their negated forms:
```python
negation_map: Dict[int, int]  # {assumption_id: negated_assumption_id}
```

**Why it exists**: Supports the **REDUCE algorithm** for redundancy elimination.

### Where Negation Map Is Built

Three sources populate the negation map:

#### 1. **Oracle (Background Knowledge)**
- File: `conacq/oracle/fm_oracle_model.py` (Part 3 of assumption ID layout)
- What: Root constraint pair + its negation
- Code:
  ```python
  bg_data = BGData(
      set_kb=[...],
      assumptions=(root_id, negated_root_id),
      negation_map={root_id: negated_root_id},  # ← Populated here
      descriptions={root_id: "root", negated_root_id: "NOT(root)"},
      next_available_id=next_id
  )
  ```

#### 2. **Bias Constraints Preparation**
- File: `conacq/algorithms/acqmss/task_preparation.py` (Part 6)
- What: Each bias constraint gets negated form via Tseitin variables
- Code:
  ```python
  for key, c in model.constraint_map.items():
      neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
      model.negated_constraint_map[f"NOT({key})"] = neg_clauses
  
  # Then prepare_kb() creates assumptions and populates negation_map
  ```

#### 3. **Negated Negative Examples (NE)**
- File: `conacq/algorithms/acqmss/task_preparation.py` (Part 8)
- What: For each NE generated from negative examples
- Code:
  ```python
  result.negation_map[ne_id] = negated_ne_id  # Maps NE ID to its negation
  ```

### How Negation Map Is Used

The **REDUCE algorithm** uses negation_map to test constraint redundancy:

```python
def reduce(set_b_prime, set_neg_tv, set_bg, negation_map):
    kb = set_b_prime ∪ set_neg_tv  # Start with KB
    for c in kb:
        neg_c = negation_map[c]  # Get ¬c
        # Check: BG ∪ (KB - {c}) ∪ {¬c} inconsistent?
        if inconsistent(set_bg + (kb - [c]) + [neg_c]):
            kb.remove(c)  # c is redundant
    return kb
```

**Logic**: If `BG ∪ (KB - {c}) ∪ {¬c}` is inconsistent, then c is **necessarily true** given BG and KB, so it's **redundant**.

### Critical Property

- **Negation map must include ALL constraints** that could be tested for redundancy
- **Missing entries cause REDUCE to skip constraints** with a warning
- **Order-independent**: Map stores assumption IDs, not constraint names

---

## 3. Oracle Example Generation and Root Handling

### Does Oracle Include Root Feature (f0) in Examples?

**YES, implicitly always included**. Here's how:

#### Example Generation Process

1. **Random Sampling** (`conacq/example_generators/random_sampling.py`):
   ```python
   features_list = sorted(self.features)  # All features INCLUDING root
   for i in range(n):
       assignments = {f: random.choice([True, False]) for f in features_list}
       # Root assigned randomly! (but oracle validation will reject if invalid)
       example_set.add(example)
   ```

2. **SAT-Based Valid Config Generation**:
   ```python
   def _generate_valid_config(features_list):
       # Uses SAT solver to generate valid configuration
       # Solver.solve() returns complete model covering ALL variables
       return {name: fid in model for name, fid in variables.items()}
       # Root is included in the model!
   ```

#### Oracle Validation Step
- When `oracle.is_valid(assignments)` is called, it:
  1. Validates the **full feature model** including root constraints
  2. Root must satisfy: `root = True` (feature model constraint)
  3. Invalid configurations (including wrong root assignments) are rejected

#### Result
- **E⁺ (positive examples)**: All have `root = True` ✓
- **E⁻ (negative examples)**: ALL have `root = True` (because oracle rejects configs where root ≠ True)
- **Root feature is never unassigned** — it's always set to True in all examples

### Root in Background Knowledge (BG)

Root is handled specially in the background knowledge:

```python
# From conacq/algorithms/interactive/learner.py
root_feature_id = feature_ids.get(fm_data.root_feature)
background = [root_feature_id] if root_feature_id is not None else []

# Later in task preparation
result.set_kb.extend(bg_data.set_kb)  # Includes root constraint assumption
result.set_b.extend(set_bg)  # Background knowledge (root)
```

**Root constraint in BG ensures**: Even if KB is empty, the SAT solver will force `root = True`.

---

## 4. Checker/Verifier Validation of Learned Constraints

### CheckerFactory and Model Integration

The checker validates learned constraints in two contexts:

#### Context 1: ConGen Algorithm (`conacq/algorithms/acqmss/congen.py`)

```python
class ConGen:
    def acquire(self, set_b, set_bg, set_tc, set_neg_tv, negation_map):
        # Step 1: Consistency check
        inconsistent = self.checker.is_consistent_test_cases(
            set_neg_tv + set_bg,  # NE ∪ BG
            set_tc,               # E+
            stop_at_first_violation=True
        )
        if inconsistent:
            return empty_KB  # Examples are inconsistent
        
        # Step 2: ACQMSS finds MSS
        b_prime = acqmss.find_mss(
            delta=[], set_b=set_b, set_neg_tv=set_neg_tv,
            set_tc=set_tc, set_bg=set_bg
        )
        
        # Step 3: REDUCE removes redundancies
        # Uses negation_map to test: BG ∪ (KB - {c}) ∪ {¬c} inconsistent?
        redundant, kb = reduce.reduce(
            set_b_prime=b_prime,
            set_neg_tv=set_neg_tv,
            set_bg=set_bg,
            negation_map=negation_map
        )
        return kb
```

#### Context 2: Accuracy Calculation (`conacq/eval/accuracy.py`)

```python
class AccuracyCalculator:
    def calculate(self, positive_examples, negative_examples):
        # For each example: Check if consistent with KB
        for example in positive_examples:
            assumptions = [fid if value else -fid 
                          for name, value in example.items()]
            accepted = self.solver.solve(assumptions=assumptions)
            # TP if accepted, FN if rejected
        
        for example in negative_examples:
            assumptions = [fid if value else -fid 
                          for name, value in example.items()]
            accepted = self.solver.solve(assumptions=assumptions)
            # TN if rejected, FP if accepted
```

### What Gets Validated

1. **Consistency Checks** (during ConGen):
   - Example assignments + acquired constraints + BG must be jointly consistent
   - Tests incremental check: `is_consistent_test_cases(negative_examples ∪ BG, positive_examples)`

2. **Redundancy Checks** (during REDUCE):
   - Each constraint c must fail to be derivable: `¬(KB - {c} ∪ BG ⊨ c)`
   - Formula: `inconsistent(BG ∪ (KB - {c}) ∪ {¬c})` ⟹ c is redundant

3. **Accuracy Checks** (evaluation):
   - KB must accept all positive examples
   - KB must reject all negative examples

---

## 5. Cross-Validation and Root Constraint Impact on Accuracy

### CV Pipeline (`conacq/eval/cross_validation.py`)

```python
def n_fold_cross_validation(runner, n_folds=5, seed=42):
    for fold_index in range(n_folds):
        # Split examples
        train_pos, train_neg = examples_without_fold_i
        test_pos, test_neg = fold_i
        
        # Learn KB on training fold
        kb_result = runner.run(train_pos, train_neg, shuffle_seed=seed)
        
        # Test accuracy on test fold
        accuracy = AccuracyCalculator(kb_result.kb_clauses, variables).calculate(
            test_pos, test_neg
        )
```

### Root Constraint Impact on Accuracy

#### Root in Background Knowledge

```python
# From ConGen acquisition
set_bg = [root_assumption_id]  # Root is always in BG

# From ConGen consistency check
is_consistent = checker.is_consistent_test_cases(
    set_neg_tv + set_bg,  # NE ∪ [root]
    set_tc                # E+
)
```

**Effect**: Root is **always enforced** during learning and accuracy checks because:
1. Root is in BG: Forces `root = True`
2. All examples have `root = True` (oracle validation)
3. KB will learn constraints that assume `root = True`

#### How Root Affects Accuracy Metrics

**Scenario 1: Root included in test examples**
- Positive examples: All have `root = True`
- Negative examples: All have `root = True`
- **Result**: Learned KB satisfies root constraint by construction → No impact on accuracy

**Scenario 2: What if root were missing from examples?**
- Would need to be handled as missing feature
- Would cause KeyError in `_is_accepted()` lookup
- **Current design prevents this** via oracle validation

#### In Clause-Based Comparison

Root constraint appears explicitly in oracle.clause_set:
```python
# From ground_truth extraction
clauses = [clause for clauses in fm_model.constraint_map.values()
           for clause in clauses]
clause_set = {tuple(sorted(c)) for c in clauses}
# Root constraint IS in this set!
```

**Impact on clause-based accuracy**:
- If KB includes root: Counts toward TP
- If KB doesn't include root: But BG includes it, so in union: Still TP (via BG)
- **Result**: Root constraint often gets counted correctly via BG union

---

## Key Findings Summary

| Aspect | Finding | Impact |
|--------|---------|--------|
| **Constraint Comparison** | Two strategies: description-based (recommended) and clause-based | Different precision levels; description catches learned intent better |
| **Negation Map** | Dict[int, int] mapping assumption IDs to negations | ESSENTIAL for REDUCE; must include all constraints tested |
| **Example Generation** | Root is always included implicitly via oracle validation | All examples valid w.r.t. root; no missing features |
| **Root Constraint** | Always in Background Knowledge (set_bg) | Enforced during ConGen; always True in learned KB |
| **Accuracy Calculation** | Separate from constraint comparison; tests KB on examples | Primary metric for generalizability; not about constraint descriptions |
| **CV Impact** | Root consistency maintained across folds | Folds share same BG; no root-related variance between folds |

---

## Unresolved Questions

1. **Does clause-based comparison always include BG clauses?** Yes (confirmed in code: `kb_clauses ∪ bg_clauses`), but should verify test coverage is complete.

2. **What happens if negation_map has missing entries?** REDUCE logs warning and skips constraint (observed behavior). Should this be an error instead?

3. **Are there any feature models where root constraint is non-trivial?** (i.e., not just `root = True`?) Current codebase assumes trivial root; should verify with complex FMs.

4. **How does FM-to-CNF conversion handle root?** Generated by `FmToDiagPysat` with `create_negation=False` — should verify the transformation includes root constraint explicitly.

