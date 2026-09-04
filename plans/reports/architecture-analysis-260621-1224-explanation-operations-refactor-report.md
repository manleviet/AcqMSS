# Architecture Analysis — PySATAbstractExplanation hierarchy + PySATExplanationBuilder

**Date:** 2026-06-21
**Branch:** `feat/phase-r-task-as-unit`
**Author:** architecture review (advisory)
**Purpose:** Hand-off to cowork for verification + planning. Advisory only — no code changed.
**Scope:** `explanation/operations/` — abstract base, 6 concrete operation subclasses, builder hierarchy.

---

## TL;DR

6 operation classes (~70 LOC each, ~420 total) are **~90% identical boilerplate**. Real variation reduces to **3 orthogonal knobs**: `(labeler_factory, solver, diagnoses_first)`. Modeled by inheritance product → combinatorial class explosion. Builder layer mirrors the duplication.

**Recommended:** Tier 1+2 (pull invariants up + fold SAT4J into `solver_name`). Skip Tier 3 (full composition) unless the algorithm set is expected to grow — YAGNI. Risk LOW–MEDIUM; well test-guarded (`tests/test_diagnosis.py`, green).

---

## Files in scope

| File | Role |
|------|------|
| `explanation/operations/pysat_abstract_explanation.py` | Abstract base (Template Method) |
| `explanation/operations/pysat_diagnosis.py` | FastDiag, glucose |
| `explanation/operations/pysat_conflict.py` | QuickXPlain, glucose |
| `explanation/operations/pysat_diagnosis_sat4j.py` | FastDiag, SAT4J |
| `explanation/operations/pysat_conflict_sat4j.py` | QuickXPlain, SAT4J |
| `explanation/operations/pysat_testcase.py` | KBDiag (+m) |
| `explanation/operations/pysat_testcase_quickxplain.py` | QuickXPlainWithTestCases |
| `explanation/operations/pysat_explanation_builder.py` | Builder hierarchy + redundancy builders |
| `explanation/operations/algorithms/checker.py` | `CheckerFactory` (solver entry points) |

---

## 1. Architecture Analysis — variation vs boilerplate

Per-subclass diff matrix:

| Subclass | `_create_labeler` (differs) | `_create_checker` (differs) | message order (differs) | rest |
|----------|------------------------------|------------------------------|--------------------------|------|
| PySATDiagnosis | FastDiag | base/glucose | `[diag, cs]` | **identical** |
| PySATConflict | QuickXPlain | base | `[cs, diag]` | **identical** |
| PySATDiagnosisSAT4J | FastDiag | **sat4j** override | `[diag, cs]` | **identical** |
| PySATConflictSAT4J | QuickXPlain | **sat4j** override | `[cs, diag]` | **identical** |
| PySATTestCase | KBDiag (+`m`) | base | `[diag, cs]` | **identical** |
| PySATTestCaseQuickXPlain | QXTestcase | base | `[diag, cs]` | **identical** |

### Smell 1 — `prepare_hsdag()` is a fake abstract method
- Declared `@abstractmethod` at `pysat_abstract_explanation.py:241-253`, docstring says *"the main extension point"*.
- But the body is **byte-identical** in all 6 subclasses:
  ```python
  def prepare_hsdag(self, task):
      checker = self._create_checker(task)
      labeler = self._create_labeler(checker, task)
      return checker, self._create_hsdag(labeler)
  ```
  (`pysat_diagnosis.py:49-61`, `pysat_conflict.py:50-62`, `pysat_diagnosis_sat4j.py:54-66`, `pysat_conflict_sat4j.py:55-67`, `pysat_testcase.py:63-75`, `pysat_testcase_quickxplain.py:42-54`).
- The **only** true extension point is `_create_labeler()`.

### Smell 2 — `set_result_messages()` varies only by order
- Two shapes: `[diag, cs]` (Diagnosis, DiagnosisSAT4J, TestCase, TestCaseQX) vs `[cs, diag]` (Conflict, ConflictSAT4J).
- 6 overrides encode a single boolean. (e.g. `pysat_diagnosis.py:63-70` vs `pysat_conflict.py:64-71`.)
- Note minor inconsistency: diagnosis/conflict use `result_messages.extend([...])`; testcase variants use `result_messages = [...]` (assignment). Same net effect on fresh instance but worth normalizing.

### Smell 3 — Cartesian class explosion: solver × labeler
- diagnosis/conflict × {glucose, SAT4J} = 4 classes for **2 orthogonal axes**.
- SAT4J `_create_checker` override is **verbatim duplicated** in the 2 SAT4J classes:
  ```python
  def _create_checker(self, task):
      return CheckerFactory.create_sat4jchecker(
          self.profiler, set_kb=task.set_kb, assumptions=task.assumptions)
  ```
  (`pysat_diagnosis_sat4j.py:49-52`, `pysat_conflict_sat4j.py:50-53`.)
- Adding a solver → +2 classes; adding a labeler → ×2 over solvers. Scales multiplicatively.

### Smell 4 — Builder duplication
- `PySATRedundancyTestCasesBuilder` (`:305`) and `PySATRedundancyConstraintsBuilder` (`:380`) do **not** subclass `PySATExplanationBuilder` → re-implement `with_solver` / `with_incremental` / `build` (`:347-377`, `:423-453`). (They legitimately skip the HSDAG `max_*` interface — but solver/incremental/build are still duplicated.)
- Two testcase builders (`PySATTestcaseBuilder:211`, `PySATTestcaseQuickXplainBuilder:266`) differ only by which operation they instantiate (`with_m` only on the first).
- `for_diagnosis_sat4j()` / `for_conflict_sat4j()` factories (`:192-208`) exist **in parallel** with `with_solver()` → the solver axis is expressed twice (as class + as method).

### CheckerFactory state (grounds Tier 2)
- `checker.py:249` `create_sat4jchecker(...)` and `:258` `create_from_task(task, solver_name='glucose3', use_incremental=...)` are **separate entry points**.
- `create_from_task` does **not** currently route `solver_name == 'sat4j'` to the SAT4J checker → that is why the SAT4J operation subclasses override `_create_checker`.
- SAT4J checker uses `jar_path` and is **non-incremental** (`checker.py:186-188`) — relevant when folding.

---

## 2. Recommendations (by ROI)

### Tier 1 — Pull invariants into base (DO; high ROI, low risk)
- Move `prepare_hsdag()` → **concrete** on `PySATAbstractExplanation` (uses existing `_create_checker` + abstract `_create_labeler` + `_create_hsdag`). Delete from all 6.
- Move `set_result_messages()` → **concrete** on base, driven by class attr `diagnoses_first: bool = True`. Conflict classes set `diagnoses_first = False`. Delete 6 overrides. Normalize `extend` vs `=`.
- Outcome: each subclass shrinks to `_create_labeler()` (3–5 LOC) + optional flag. ~360 LOC → ~50. No behavior change.

### Tier 2 — Fold SAT4J into `solver_name` (DO; removes an axis)
- Route `solver_name == 'sat4j'` inside `CheckerFactory.create_from_task` → `create_sat4jchecker`.
- Delete `PySATDiagnosisSAT4J`, `PySATConflictSAT4J` + `for_diagnosis_sat4j()` / `for_conflict_sat4j()`. Use `.with_solver('sat4j')`.
- 6 → 4 operation classes; solver leaves the inheritance tree, becomes a parameter.
- **Care:** SAT4J is non-incremental + jar-based. Validate/ignore `use_incremental` when `solver_name == 'sat4j'` to avoid a meaningless combo.

### Tier 3 — Compose instead of inherit (CONSIDER; only if algorithm set grows)
- Collapse remaining 4 subclasses into one config-driven `PySATExplanation` parameterized by `(ParamsClass, LabelerClass, diagnoses_first)` — every `_create_labeler` follows the same shape `XParameters(set_c, set_b[, set_tc, set_neg_tv]) → XLabeler(checker, [m,] params)`.
- **YAGNI caveat:** the algorithms (FastDiag, QuickXPlain, KBDiag, QXTestcase) are academic + stable. Tier 3 trades the readable "one file per algorithm" shape for marginal LOC. **Recommend stopping at Tier 1+2** unless many new labelers/solvers are planned.

### Tier 4 — Builder cleanup (LOW priority)
- Small shared mixin `_SolverConfigurableBuilder` carrying `with_solver` / `with_incremental` / `build` for redundancy builders + main builder.
- Merge the two testcase builders if `with_m` can default.

---

## 3. Implementation strategy (suggested sequencing for planner)

1. **Tier 1** first — mechanical, fully covered by `tests/test_diagnosis.py` (462 LOC, green). One commit.
2. **Tier 2** — touches `CheckerFactory`; verify incremental/jar semantics. Separate commit (easy revert).
3. Re-evaluate: if tree is clean enough, **skip Tier 3** (YAGNI).
4. **Tier 4** optional.

Estimated reduction: operations ~420 LOC → ~120 LOC (base concrete + 4 thin subclasses), minus 2 classes from Tier 2.

---

## 4. Risk assessment

- **Risk: LOW–MEDIUM.** Internal operations, not public API; dense test coverage, currently green.
- Tier 2 watch-point: SAT4J non-incremental + `jar_path` — routing must preserve semantics; decide validation for `.with_solver('sat4j').with_incremental(True)`.
- Honest framing: this is **boring boilerplate, not dangerous debt**. Tier 1 alone captures ~80% of the value (removes the blatant copy-paste) at near-zero risk. A full composition rewrite (Tier 3) is over-engineering for a stable algorithm set.

---

## 5. Verification checklist for cowork

- [ ] Confirm `prepare_hsdag` bodies are byte-identical across all 6 (cite lines above).
- [ ] Confirm `_create_checker` SAT4J override is identical in both SAT4J classes.
- [ ] Confirm `CheckerFactory.create_from_task` does not already route `sat4j` (`checker.py:258`).
- [ ] Confirm SAT4J checker is non-incremental (`checker.py:186-188`) — affects Tier 2 validation.
- [ ] Run `uv run --no-sync pytest tests/test_diagnosis.py -v` as the regression gate before/after.
- [ ] Grep external callers of `for_diagnosis_sat4j` / `for_conflict_sat4j` / `PySAT*SAT4J` before deleting (apps/, tests/, conacq/).

---

## Unresolved questions

1. Is the algorithm/solver set expected to **grow** (e.g. cadical, new labelers)? Yes → Tier 3 earns its keep; No → stop at Tier 1+2.
2. Is `.with_solver('sat4j')` + `with_incremental(True)` a valid combo, or is SAT4J always non-incremental? Decides Tier 2 validation behavior.
3. Are there external callers of the `*SAT4J` operation classes or `for_*_sat4j()` factories outside `explanation/`? Must grep before Tier 2 deletion.
