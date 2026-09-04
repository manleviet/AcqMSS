# Research: QuAcq & GenerateNE neg_c_map Usage

## Q1: QuAcq neg_c_map Usage & REDUCE Step

**File:** `acqmss/algorithms/interactive/quacq.py`

QuAcq **does NOT use neg_c_map** directly in the interactive loop. However, it calls REDUCE in `_reduce_kb()` (line 330+):

```python
def _reduce_kb(self, task: InteractiveTask) -> List[str]:
    neg_map = {}
    clauses_to_name = {}
    for c_id in task.learned_kb:
        if c_id in task.constraint_map and c_id in task.negated_constraint_map:
            clauses = task.constraint_map[c_id]
            clauses_key = tuple(tuple(c) for c in clauses)
            clauses_to_name[clauses_key] = c_id
            neg_map[c_id] = task.negated_constraint_map[c_id]

    redundant, non_redundant = reduce.reduce(
        set_b_prime=set_b_prime,
        set_ne=[],
        set_bg=set_bg,
        neg_map=neg_map,  # <-- REDUCE uses this
        name_lookup=clauses_to_name
    )
```

**Key:** QuAcq builds neg_map from `task.negated_constraint_map` at reduction time. It does not populate `neg_c_map` in task.

---

## Q2: GenerateNE neg_map for Non-Incremental Mode

**File:** `acqmss/algorithms/generate_ne.py` (lines 80-130)

GenerateNE produces **different neg_map formats** per mode:

**Incremental mode:**
```python
# Keys: assumption IDs (int), Values: negated assumption IDs (int)
neg_map[assumption_id] = neg_assumption_id
```
- Each NE constraint gets two assumptions: one for the blocking clause, one for its negation
- Example: `neg_map[1000] = 1001`

**Non-incremental mode:**
```python
# Keys: constraint names (str), Values: negated clause lists (List[List[int]])
ne_name = f"ne_{ne_index}"
ne_negated = [[lit] for lit in minimal_conflict]
neg_map[ne_name] = ne_negated
```
- NE constraint named `"ne_0"`, negated form stored as unit clause list
- Example: `neg_map["ne_0"] = [[1], [2]]` (DNF: 1 ∨ 2)

Both modes return `NEResult` with `neg_map` field.

---

## Q3: CONGEN Merges GenerateNE neg_map into task.neg_c_map

**File:** `acqmss/algorithms/congen.py` (line 140)

```python
# Step 1: NE ← GENERATENE(E⁻)
ne_result = generate_ne.generate(
    set_tv=task.e_neg_literals,
    set_bg=task.set_b,
    start_assumption_id=task.next_assumption_id
)

# Merge NE neg_map into task for REDUCE
task.neg_c_map.update(ne_result.neg_map)  # <-- MERGE HERE
```

**Flow:**
1. GenerateNE returns `NEResult.neg_map` (int→int for incremental, str→list for non-incremental)
2. Task receives `.update()` call; adds GenerateNE's negated forms to task.neg_c_map
3. REDUCE later uses `task.neg_c_map` with merged entries

**Key difference:** Bias constraints populate neg_c_map in task prep (task_preparation.py), NE constraints added dynamically by CONGEN.

---

## Q4: Other Mapping Mechanisms in interactive/

**Directory contents:**
- `task.py`: InteractiveTask with `constraint_map`, `negated_constraint_map`
- `findc.py`: Finds specific constraint during conflict resolution (uses constraint_map)
- `findscope.py`: Finds variable scope for negative examples
- `query_generator.py`: Generates test queries (uses feature_ids)
- `learner.py`: Main entry point, orchestrates QuAcq
- `user_interface.py`: Oracle abstraction
- `result.py`: Result container

**No other neg_c_map.** Interactive module relies on:
- `constraint_map` (name → clauses)
- `negated_constraint_map` (name → negated clauses)
- NOT on neg_c_map (that's CONGEN-specific)

---

## Q5: Tests for neg_c_map Behavior

**File:** `tests/test_diagnosis.py` (line 1196)

```python
neg_cf_map = model.get_neg_c_map()
print(f"neg_cf_map: {neg_cf_map}")
assert len(neg_cf_map) > 0, "Should have negated forms"
```

Test calls `model.get_neg_c_map()` on CONGENModel. This likely returns task.neg_c_map after CONGEN finishes. Test validates that negated forms were populated (from bias constraints in task prep).

**No direct test of GenerateNE neg_map merge.** Test validates end state only.

---

## Summary Table

| Component | neg_c_map Type | Populated When | Used By |
|-----------|---|---|---|
| **Bias constraints** | `int → int` (incr) or `str → list` (non-incr) | Task prep | REDUCE (via CONGEN) |
| **GenerateNE output** | Same as bias | CONGEN.acquire() line 140 | REDUCE |
| **QuAcq** | Does NOT use neg_c_map; builds ad-hoc neg_map | End of learning | REDUCE (internal call) |

---

## Unresolved Questions

1. Why does QuAcq NOT use task.neg_c_map but builds its own neg_map in _reduce_kb()? Is this intentional design or legacy code?
2. Does InteractiveTask.negated_constraint_map ever get populated? Where?
3. What's the purpose of `clauses_to_name` mapping in non-incremental mode task prep? Is it for reverse lookup?
