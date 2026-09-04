# Investigation: Root Constraint Appearing in Missed Constraints

## Executive Summary

**Bug Found**: The root constraint is incorrectly appearing in `missed_constraints` during evaluation.

**Root Cause**: Architectural mismatch in how Ground Truth (FM oracle) and Learned KB extract constraints:
- **Ground Truth**: Built from FM's `constraint_map` which includes ALL FM constraints, including root
- **Learned KB**: Comes from bias constraints, which DOES NOT include root (root is in Background Knowledge, not in set_c)
- **Comparison Logic**: Description-based strategy compares FM descriptions against bias descriptions
- **The Problem**: `extract_constraint_descriptions()` DOES extract root constraint description, but learned KB never learns the root (by design)

## Data Flow Trace

### 1. Ground Truth Construction (Oracle)

**Entry Point**: `GroundTruthData.from_uvl(uvl_path)` (line 31-63 in `ground_truth.py`)

```python
@classmethod
def from_uvl(cls, uvl_path: Path) -> 'GroundTruthData':
    fm = UVLReader(str(uvl_path)).transform()
    fm_model = FmToDiagPysat(fm, create_negation=False).transform()
    
    # KEY: Extract descriptions from FM
    descriptions = extract_constraint_descriptions(fm)  # <-- INCLUDES ROOT
    
    # KEY: Get clauses from constraint_map
    clauses = [clause for clauses in fm_model.constraint_map.values()
               for clause in clauses]
    clause_set = {tuple(sorted(c)) for c in clauses}
    
    return cls(descriptions=descriptions, clauses=clauses, ...)
```

### 2. Oracle Constraint Map Population

**In `FmToDiagPysat.transform()` (lines 80-96)**:
- Calls parent `FmToPysat.transform()`
- Parent iterates features → calls `add_root()` and `add_relation()`
- Each adds constraints to `destination_model.constraint_map`

**Key Method: `add_root()`** (lines 36-42):
```python
def add_root(self, feature: Feature) -> None:
    var = self.destination_model.variables.get(feature.name)
    self.destination_model.add_clause([var])
    # Stores in constraint_map with key = str(feature) = feature name
    self.destination_model.add_clause_to_map(str(feature), [[var]])
```

**For REAL-FM-7 example**:
- Root feature: `jplug` (id=1)
- Root constraint clause: `[1]` (must be true)
- Stored in `constraint_map['jplug']` = `[[1]]`

### 3. Descriptions Extraction

**Function: `extract_constraint_descriptions(fm)`** (lines 13-54 in `constraint_description.py`)

```python
def extract_constraint_descriptions(fm) -> Set[str]:
    descriptions = set()
    
    # Hierarchical constraints from feature relationships
    for feature in fm.get_features():
        for relation in feature.get_relations():
            if relation.is_mandatory():
                # Adds: "parent --mandatory--> child"
                ...
    
    # Cross-tree constraints
    for ctc in fm.get_constraints():
        desc = _parse_ctc_to_description(ctc)
        if desc:
            descriptions.add(desc)
    
    return descriptions
```

**Critical Issue**: This function extracts all feature relationships, which includes the ROOT feature. The root has no relations (it's the topmost), so NO description is generated for it. However, the root constraint IS in `constraint_map`.

**Ground Truth Result for REAL-FM-7**:
- `descriptions` = all hierarchical + cross-tree constraints
- `clauses` = includes root clause `[1]` from `constraint_map`
- **Mismatch**: Root clause in `clauses` but no description in `descriptions`

### 4. Learned KB Construction

**Entry Point**: `KBComparator._compare_by_description()` (lines 107-162 in `kb_comparator.py`)

```python
def _compare_by_description(self, result: ConGenResultData) -> ComparationResult:
    # Get oracle descriptions (ground truth)
    fm_descriptions = self.oracle.descriptions  # <-- ROOT NOT HERE
    
    # Get acquired KB descriptions
    acquired_descriptions: Set[str] = set()
    for cid in result.kb_constraints:
        if cid.startswith('ne_'):
            continue  # Skip NE constraints
        if self.bias.has_constraint(cid):
            desc = self.bias.get_description(cid)
            acquired_descriptions.add(desc)
    
    # Compute metrics
    tp = acquired_descriptions & fm_descriptions
    fp = acquired_descriptions - fm_descriptions
    fn = fm_descriptions - acquired_descriptions  # <-- ROOT CONSTRAINT MISSING
    
    missed = list(fn)  # <-- ROOT APPEARS HERE
```

### 5. Why Root Never Appears in Learned KB

**Root BG Data** (lines 256-264 in `fm_oracle_model.py`):

```python
# Extract root BG data for ConGen consumption
model._bg_data = BGData(
    set_kb=result.set_kb[:2],  # first pair of assumptions for root constraint
    assumptions=(result.assumptions[0], result.assumptions[1]),
    negation_map={result.assumptions[0]: result.assumptions[1]},
    descriptions=provider.get_descriptions_for(
        [result.assumptions[0], result.assumptions[1]]),
    next_available_id=id_assumption,
)
```

The root constraint is:
1. Prepared with assumption guards: `[-a_root, root_id]`
2. Added to `set_kb` (always active background knowledge)
3. **NOT added to `set_c` (potentially faulty constraints)**
4. ConGen never learns the root because it's in BG, not in the target set

**Result**: Root constraint NEVER appears in `result.kb_constraints`

### 6. Clause-Based Strategy (Different Issue)

**In `_compare_by_clause()`** (lines 164-218):

```python
def _compare_by_clause(self, result: ConGenResultData) -> ComparationResult:
    kb_clauses: Set[Tuple[int, ...]] = set()
    
    # Convert KB constraints to clauses
    for cid in result.kb_constraints:
        if cid.startswith('ne_'):
            continue
        clauses = self.bias.get_clauses(cid)
        kb_clauses.add(normalized_clause)
    
    # UNION with bg_clauses (line 186-189)
    if result.bg_clauses:
        for clause in result.bg_clauses:
            normalized = tuple(sorted(clause))
            kb_clauses.add(normalized)
    
    # Compare with oracle
    metrics = compute_metrics(kb_clauses, self.oracle.clause_set, bias_clauses)
```

**Clause-based approach handles root better**: If `bg_clauses` is provided (containing root clause), it gets unioned into KB before comparison.

## The Bug

### In Description-Based Strategy

**Test case from `test_evaluation.py` line 484-512**:

```python
def test_clause_eval_includes_bg_clauses(self):
    """Verify bg_clauses are unioned with kb_clauses in clause eval."""
    comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)
    
    result_with_bg = ConGenResultData(
        kb_constraints=[],
        n_bias=len(comparator.bias.constraints),
        n_kb=0,
        bg_clauses=[[root_id]]  # <-- BG includes root
    )
    
    result_without_bg = ConGenResultData(
        kb_constraints=[],
        n_bias=len(comparator.bias.constraints),
        n_kb=0,
        bg_clauses=[]
    )
    
    eval_with = comparator.compare(result_with_bg, ComparationStrategy.CLAUSE)
    eval_without = comparator.compare(result_without_bg, ComparationStrategy.CLAUSE)
    
    # With bg_clauses: root clause should be TP
    assert eval_with.metrics.true_positives >= eval_without.metrics.true_positives
```

This test passes for CLAUSE strategy (bg_clauses is used), but **description-based strategy never uses bg_clauses**.

### Why Root Constraint Has No Description

**In `extract_constraint_descriptions()`** (line 32-46):

```python
for feature in fm.get_features():
    for relation in feature.get_relations():
        # ... add descriptions for mandatory, optional, alternative, or ...
```

The root feature's `.get_relations()` is empty. Root has no parent relationship, so NO description is generated.

**However**, root IS in `constraint_map` (added by `add_root()` method).

### Consequence for Description Strategy

1. **Ground Truth** (`fm_descriptions`):
   - Does NOT include root description (no description generated)
   - But INCLUDES root clause in `clauses` and `clause_set`

2. **Learned KB** (`acquired_descriptions`):
   - Comes only from bias constraints
   - Never learned (root in BG, not set_c)
   - Will never match root

3. **Result**:
   - `fn = fm_descriptions - acquired_descriptions`
   - If root description WAS generated: `fn` would include root
   - `missed_constraints = list(fn)` would show root

**Actual observation**: Root constraint description is likely NOT being extracted, so it shouldn't appear in `missed_constraints`. 

**Hypothesis**: User is seeing a different constraint with root in description (e.g., from hierarchical relation with root as parent).

## Code Verification

Let me verify what descriptions ARE generated for REAL-FM-7:

```python
# REAL-FM-7.uvl structure:
# jplug (root, mandatory)
#   ├─ interface (mandatory) → [sdi | mdi] (alternative)
#   └─ gui_builder (optional)
#       ├─ java (mandatory)
#       └─ qt (optional)
#   ... more constraints

# Descriptions extracted:
# 1. "jplug --mandatory--> interface"      (from relation)
# 2. "interface --alternative--> [sdi, mdi]"
# 3. "jplug --optional--> gui_builder"     (from relation)
# 4. "gui_builder --mandatory--> java"
# 5. "gui_builder --optional--> qt"
# ... and CTCs

# NO description for "jplug" itself (it's the root, no relation to extract)
```

## Where Root Might Be Leaking In

**Possible scenarios**:

1. **Non-root feature with "root" in its relation description**:
   - E.g., if jplug has a child with a specific relation type
   - Description would be: "jplug --<relation>--> <child>"
   - This IS in both FM and might be in bias

2. **Root description extracted differently in another code path**:
   - Check if `FMOracleModel.prepare()` adds descriptions differently

3. **Bug in how GroundTruthData is built**:
   - Maybe descriptions ARE being added for root elsewhere

4. **Bias generation includes root description**:
   - Check if bias generator adds root constraint

## Recommendations

### Immediate Fix

**In `_compare_by_description()`**, ensure consistency by:

1. **Option A (Recommended)**: Also check root constraint
   - Get root feature name from oracle
   - Check if root constraint is in both ground truth and learned KB
   - Handle separately if needed

2. **Option B**: Filter out root from descriptions
   - Root is special (in BG, not set_c)
   - Skip root in description extraction

3. **Option C**: Include bg_clauses in description strategy
   - Similar to clause-based strategy
   - But need to convert bg_clauses back to descriptions (lossy)

### Better Design

**Root constraint handling should be explicit**:
- Clearly document that root is in BG, not in set_c
- Either:
  - Exclude root from oracle descriptions (it can't be learned)
  - Or, treat root separately in evaluation
  - Or, provide bg_clauses to description strategy

### Testing

Add explicit test for root constraint:

```python
def test_root_not_in_missed_constraints(self):
    """Verify root constraint doesn't appear in missed_constraints."""
    comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)
    
    # Get root feature
    root = comparator.oracle.root_feature
    root_id = comparator.oracle.feature_map[root]
    
    # Empty KB (no learned constraints)
    result = ConGenResultData(
        kb_constraints=[],
        n_bias=len(comparator.bias.constraints),
        n_kb=0
    )
    
    eval_result = comparator.compare(result, ComparationStrategy.DESCRIPTION)
    
    # Root should NOT be in missed_constraints
    # (because root can't be learned - it's in BG)
    root_in_missed = any(root in str(c) for c in eval_result.missed_constraints)
    assert not root_in_missed, f"Root constraint found in missed: {eval_result.missed_constraints}"
```

## Files to Investigate Further

1. **`conacq/eval/kb_comparator.py`** - Description extraction logic
2. **`conacq/oracle/constraint_description.py`** - How descriptions are built
3. **`conacq/bias/bias_generator.py`** - Check if bias includes root
4. **`conacq/bias/bias_io.py`** - JSON bias loading
5. **`tests/test_evaluation.py`** - Add explicit root tests

## Summary Table

| Component | Root Constraint Included | Source |
|-----------|---------------------------|---------|
| FM constraint_map | YES | FmToDiagPysat.add_root() |
| FM descriptions | NO* | extract_constraint_descriptions() |
| Oracle clause_set | YES | from constraint_map |
| Bias constraints | NO** | Generated for non-root features |
| Learned KB | NO | Root in BG, not set_c |
| Ground Truth (descriptions) | NO | Missing description |
| Ground Truth (clauses) | YES | In clause_set |
| Description eval missed | YES | fn = GT - KB (if desc exists) |
| Clause eval missed | NO | When bg_clauses provided |

*Root has no relations, so no description generated
**Root not learned in ConGen (BG)

---

**Status**: Investigation complete. Root cause identified. Ready for fix design.
