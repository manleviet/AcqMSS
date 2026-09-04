# QuAcq Internal Data Dependencies

**Date:** 2026-02-28
**Scope:** DiscriminatingGenerator, QueryGenerator, FindScope, FindC, Reduce usage

---

## 1. DiscriminatingGenerator

**File:** `conacq/algorithms/quacq/discriminating_generator.py`

### `__init__` stores:
- `self._task` — full `QuAcqTask` reference
- `self._solver_name` — string

### `generate(c_i, c_j, learned_kb, scope)` accesses:
| Field | Usage |
|---|---|
| `task.background_clauses` | BG clauses added to SAT formula |
| `task.constraint_clauses.get(c_i)` | Clauses c_i must satisfy |
| `task.negated_clauses.get(c_j)` | Negated form c_j must violate |
| `task.model_to_config(model)` | Convert SAT model → config dict |
| `task._get_constraint_vars(c_id)` | (internal) Filter learned KB to scope |
| `task.constraint_clauses.get(c_id)` | (internal) Fetch clauses for C_L[Y] |

**Summary:** needs `background_clauses`, `constraint_clauses`, `negated_clauses`, `model_to_config()`, `_get_constraint_vars()`.

---

## 2. QueryGenerator

**File:** `conacq/example_generators/query_generator.py`

### `generate(task, remaining_bias, learned_kb)` accesses:
| Field | Usage |
|---|---|
| `task.set_b` | Logged: `len(task.set_b)` |
| `task.get_kb_clauses(kb)` | Resolve learned KB → clauses |
| `task.negated_clauses.get(c_id)` | Via `_get_negated_clauses()` helper |
| `task.feature_ids` | Passed to `_try_generate_for_constraint` |
| `task.id_to_feature` | Passed to `_try_generate_for_constraint` |
| `get_bg_clauses(task)` | Via `_task_compat.get_bg_clauses` (wraps `task.background_clauses` or `task.bg_clauses`) |

**Summary:** needs `set_b` (len only), `get_kb_clauses()`, `negated_clauses`, `feature_ids`, `id_to_feature`, BG clauses accessor.

---

## 3. FindScope

**File:** `conacq/algorithms/quacq/findscope.py`

### `find_scope(e, R, Y, ask_query, oracle, task, remaining_bias, record_query, profiler)` accesses:
| Field | Method | Usage |
|---|---|---|
| `task.partial_config_to_assumptions(e, R)` | method | Convert partial config → assumption literals |
| `task._get_constraint_vars(c_id)` | method | Check if constraint scope ⊆ R |
| `task.violates_clauses(clauses, assignment)` | method | Check if constraint rejects partial config |
| `get_clause_map(task)` | compat wrapper | Returns `task.constraint_clauses` |

**Mutates:** `remaining_bias` (set passed in — not a task field)

**Summary:** needs `partial_config_to_assumptions()`, `_get_constraint_vars()`, `violates_clauses()`, `constraint_clauses`.

---

## 4. FindC

**File:** `conacq/algorithms/quacq/findc.py`

### `find_c(e, scope, task, remaining_bias, record_query, oracle, learned_kb, generator, ...)` accesses:
| Field | Method | Usage |
|---|---|---|
| `task.get_constraints_with_scope(scope, remaining_bias)` | method | Get candidate constraint IDs |
| `task.config_to_assumptions(e)` | method | Convert config → assumption literals |
| `task.violates_clauses(clauses, assignment)` | method | Check candidate rejection |
| `get_clause_map(task)` | compat wrapper | Returns `task.constraint_clauses` |

**Calls `generator.generate(c_i, c_j, learned_kb, scope)`** — see §1.

**Summary:** needs `get_constraints_with_scope()`, `config_to_assumptions()`, `violates_clauses()`, `constraint_clauses`.

---

## 5. Reduce Usage in QuAcq

**File:** `quacq.py` → `_apply_reduce(task, learned_kb)`

```python
checker = NonIncrementalPySATChecker(
    task.set_kb, task.assumptions, self.solver_name, self.profiler)
reduce = Reduce(checker, self.profiler)
reduce.reduce(
    set_b_prime=learned_kb,
    set_neg_tv=[],
    set_bg=task.set_b,
    negation_map=task.negation_map
)
```

| Field | Usage |
|---|---|
| `task.set_kb` | Passed to checker constructor |
| `task.assumptions` | Passed to checker constructor |
| `task.set_b` | BG for Reduce (set_bg parameter) |
| `task.negation_map` | Negation map for Reduce |

**Summary:** needs `set_kb`, `assumptions`, `set_b`, `negation_map`.

---

## 6. QuAcq Main Loop (quacq.py)

Additional direct `task.*` accesses in `learn()` / `learn_from_examples()`:

| Field | Usage |
|---|---|
| `task.set_c` | Initial `remaining_bias = set(task.set_c)` |
| `task.feature_ids.keys()` | `all_variables` set for FindScope Y arg |
| `task.config_to_assumptions(positive_example)` | `_prune_rejecting_constraints` |
| `task.violates_clauses(clauses, assignment)` | `_prune_rejecting_constraints` |
| `get_clause_map(task)` | `_prune_rejecting_constraints` |

`_build_result` additionally calls `get_clause_map(task)` for `initial_bias_size`.

---

## 7. Consolidated Field Map

| `QuAcqTask` field/method | Accessed by |
|---|---|
| `set_c` | QuAcq main loop |
| `set_b` | QuAcq (`_apply_reduce`), QueryGenerator |
| `set_kb` | `_apply_reduce` → checker |
| `assumptions` | `_apply_reduce` → checker |
| `negation_map` | `_apply_reduce` → Reduce |
| `feature_ids` | QueryGenerator, QuAcq main loop |
| `id_to_feature` | QueryGenerator |
| `background_clauses` | DiscriminatingGenerator, `_task_compat.get_bg_clauses` |
| `constraint_clauses` | DiscriminatingGenerator, FindScope, FindC, `get_clause_map` |
| `negated_clauses` | DiscriminatingGenerator, QueryGenerator |
| `config_to_assumptions()` | QuAcq prune, FindC |
| `partial_config_to_assumptions()` | FindScope |
| `violates_clauses()` | QuAcq prune, FindScope, FindC |
| `get_kb_clauses()` | QueryGenerator |
| `get_constraints_with_scope()` | FindC |
| `model_to_config()` | DiscriminatingGenerator |
| `_get_constraint_vars()` | DiscriminatingGenerator (internal), FindScope |

---

## 8. Refactoring Implications

1. **DiscriminatingGenerator stores full task** — tighten to only `background_clauses`, `constraint_clauses`, `negated_clauses`, `model_to_config`, `_get_constraint_vars`. DI candidate: inject a `ConstraintStore` protocol.

2. **QueryGenerator is task-agnostic** — already uses duck typing (`hasattr` guards). Only needs `set_b` (len), `get_kb_clauses()`, `negated_clauses`, `feature_ids`, `id_to_feature`, BG clauses. Could receive a minimal `QueryContext` dataclass.

3. **FindScope / FindC receive `task` as a plain arg** — not stored; already loosely coupled. Methods needed: `partial_config_to_assumptions`, `config_to_assumptions`, `violates_clauses`, `_get_constraint_vars`, `get_constraints_with_scope`. All are computation methods — good protocol boundary.

4. **`_task_compat.get_clause_map` / `get_bg_clauses`** — thin shim layer already exists; any refactor must keep or inline these.

5. **Reduce receives explicit field values** (`set_kb`, `assumptions`, `set_b`, `negation_map`) — already decoupled from task; no change needed.

6. **`_get_constraint_vars` is "private"** but called from DiscriminatingGenerator and FindScope — must be surfaced to a protocol if task is to be abstracted.

---

## Unresolved Questions

- What does `_task_compat.get_bg_clauses` do exactly — does it differ from `task.background_clauses`? (Likely handles both `QuAcqTask` and legacy `InteractiveTask` field names.)
- Is `task.set_kb` the full CNF formula or only the background? (Needed to confirm Reduce checker wiring.)
- Does `_get_constraint_vars` need to remain private or can it be promoted to the public API for a clean protocol?
