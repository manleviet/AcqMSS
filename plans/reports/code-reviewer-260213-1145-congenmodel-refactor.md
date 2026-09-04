# Code Review: CONGENModel Refactor

**Date:** 2026-02-13
**Scope:** @dataclass -> regular class with prepare()/task/description_provider
**Tests:** 13/13 passed

## Overall Assessment

Clean refactor. CONGENModel now mirrors DiagnosisModel's prepare/task/description_provider pattern. The consolidation from Incremental/NonIncremental variants to a single unified class is well-executed. All callers properly updated. No remaining references to old API.

## Pattern Consistency with DiagnosisModel

| Aspect | DiagnosisModel | CONGENModel | Match? |
|--------|---------------|-------------|--------|
| `_task` / `_description_provider` private fields | Yes | Yes | OK |
| `task` property with RuntimeError guard | Yes | Yes | OK |
| `description_provider` property with guard | Yes | Yes | OK |
| `prepare()` returns task | Yes | Yes | OK |
| Local import in `prepare()` to avoid cycles | No (uses factory) | Yes (local import) | Acceptable |
| `__init__` sets defaults | Yes | Yes | OK |

The local import in `prepare()` (line 65 of `model.py`) is a pragmatic solution for the circular dependency `model.py <-> task_preparation.py`. DiagnosisModel avoids this by using a factory in a separate module, but the local import approach is fine for a simpler hierarchy.

## Issues Found

### HIGH: CONGENRunner Missing background_knowledge (Confidence: 9/10)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/congen_runner.py` lines 157-162

```python
model = CONGENModel.from_bias_and_examples(
    bias_constraints=bias_clauses,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=self.feature_ids
    # background_knowledge NOT passed -- defaults to []
)
```

`CONGENRunner` does not pass `background_knowledge`, so `set_b` will always be empty during cross-validation runs. Compare with `apps/run_congen.py` line 134-140 which correctly passes `background_knowledge=[root_feature_id]`.

**Impact:** Cross-validation evaluations run without root feature in BG. This may produce different (potentially incorrect) KB results compared to direct `run_congen.py` runs. CONGEN's consistency check uses `set_ne + task.set_b` -- empty BG changes solver behavior.

**Fix:** Add `background_knowledge` parameter to `CONGENRunner.__init__()` or `run()`, and pass it through to `from_bias_and_examples()`. The caller in `cross_validation.py` needs to supply `[root_feature_id]`.

### MEDIUM: Type Hint Mismatch in Strategy Pattern (Confidence: 8/10)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py` line 224

The abstract base class `TestCaseTaskPreparationStrategy.prepare()` declares `model: 'DiagnosisModel'`, but `CONGENTaskPreparation.prepare()` at `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py` line 41 takes `model: CONGENModel`.

This is a Liskov substitution violation. Not a runtime error (Python duck-types), but `mypy --strict` would flag it. Both models share the same duck-typed interface (`constraint_map`, `negated_constraint_map`, `variables`, `task_input`, `next_tseitin_var`, `background_knowledge`), so an explicit protocol/ABC could formalize this.

**Recommendation:** Either create a shared `Protocol` (e.g., `TaskPreparationModel`) that both `DiagnosisModel` and `CONGENModel` implement, or change the abstract type hint to `Any` with a docstring contract.

## Positive Observations

- `root_feature_id: Optional[int]` replaced by `background_knowledge: List[int]` -- more general, supports multiple BG literals
- `extend` instead of `append` at `task_preparation.py:77` -- correctly handles multi-element BG
- Old `IncrementalCONGENTask` / `NonIncrementalCONGENTask` / dual preparation classes fully removed -- clean elimination
- `assert isinstance(output.task, CONGENTask)` at `model.py:70` -- defensive type check before assignment
- All callers (`run_congen.py`, `congen_runner.py`, `test_congen.py`) updated to new API

## Callers Audit

| Caller | Uses `from_bias_and_examples` | Passes `background_knowledge` | Uses `model.prepare()` |
|--------|------------------------------|------------------------------|----------------------|
| `apps/run_congen.py:134` | Yes | Yes (`[root_feature_id]`) | Yes |
| `acqmss/eval/congen_runner.py:157` | Yes | **NO** (defaults to `[]`) | Yes |
| `tests/test_congen.py:90` | Yes | Yes (`[root_id]`) | Yes |

## Unresolved Questions

1. **Is empty BG in CONGENRunner intentional?** Verified: the old code (commit `66b29d1`) also did NOT pass `root_feature_id` to `from_bias_and_examples()`, so BG was already empty in cross-validation before this refactor. **This is a pre-existing gap, not a regression.** However, it means cross-validation results differ from direct `run_congen.py` runs (which do pass root). Worth addressing separately if BG consistency across evaluation modes matters.
