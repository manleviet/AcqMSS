# Code Review — A2 AbstractModelBuilder Extraction

**Scope:** Working-tree changes only (4 modified + 1 new file). Branch `feat/redesign-abc`.
**Verdict: PASS** — behavior-preserving, no weakened tests, base earns its place.
**Status: DONE_WITH_CONCERNS** (one trivial dead import; non-blocking).

## Scope
- New: `explanation/models/abstract_model_builder.py`
- Modified: `explanation/models/__init__.py`, `explanation/models/diagnosis_model_builder.py`, `conacq/algorithms/acqmss/congen_model_builder.py`, `conacq/algorithms/quacq/quacq_model_builder.py`
- Net: +47 / -119 (DRY win). Tests: **376 passed, 1 warning** (= baseline; known `TestSuiteReader` PytestCollectionWarning only).

## VERIFY checklist results

### 1. Behavior-preserving (CRITICAL) — PASS
Diffed base `build()` against committed ConGen/QuAcq `build()` line-for-line:
- `_validate()` body identical (bias_path + oracle None-checks, same ValueError strings).
- Negation block byte-identical: `next_available_id` seed → `negate_cnf_tseitin` loop → `NOT({key})` keys → `next_available_id` set.
- `model.constraint_map = bias.to_constraint_map()` / `model.variables = bias.feature_ids` preserved.
- ConGen auto-prepare moved verbatim into `_post_negation_build` (resets `last_task=None`, gated on `_has_examples()`, same `_make_task_input(model, pos, neg or [])`, same `prepare_task(task_input, self._oracle)`).
- QuAcq `_post_negation_build` = `self.last_task = model.prepare_task(self._oracle)` (always-prepare, unchanged).
- Diagnosis `build()` fully overridden — same source None-check + `_create_model()`; untouched.

Runtime dispatch correct: `from_bias` is a classmethod returning `cls()` → subclass instance; `with_oracle`/`with_negation` return `self`; `build()` resolves `_create_model_instance`/`_post_negation_build` via MRO. Runner chaining (`congen_runner.py:114-117`, `quacq_runner.py:175-178`) and `.last_task` access (`test_congen.py:288`, `test_quacq.py:55`, `test_assumption_slicer.py:309`) all still valid. **376 green.**

### 2. No weakened assertions — PASS
`git diff --name-only` = the 4 source files only; **zero test files modified** (working tree + untracked). Report claim "zero test rewrites" verified. `last_task`/`with_examples`/`auto_prepare_*` paths exercised in `test_congen.py:276-362`, `test_quacq.py`, `test_assumption_slicer.py` — unchanged and passing.

### 3. Base earns its place (KISS/YAGNI) — PASS
The shared part is **real duplication**: ConGen/QuAcq `build()` had a byte-identical validate+load+negation skeleton (spec called this out: `congen:108-122 ≈ quacq:57-71`). Collapsing it into one `build()` + two tiny hooks is a genuine DRY win, not a contortion.

Diagnosis's partial inheritance is legitimate, not forced:
- It shares the **real** common surface: `_bias_path`/`_oracle`/`_create_negation` state, `with_negation`, and the `for_redundancy = with_negation` alias.
- It overrides `build()` entirely (different source model: fide/uvl/dimacs/object, no oracle) — correct: it does **not** inherit the bias skeleton it can't use.
- Template hooks `_create_model_instance`/`_post_negation_build` are unused by Diagnosis, but they're **concrete no-op/raise defaults on the base**, not `@abstractmethod`. So Diagnosis is not forced to stub them, and instantiation never errors. This is the right trade: the hooks cost Diagnosis nothing.

Verdict: base is sound. The "partially-shared" shape is acceptable per the spec's own guidance — shared part (negation skeleton + negation flag/alias) is genuine duplication.

### 4. Boundary — PASS
Base at `explanation/models/abstract_model_builder.py`, re-exported in `explanation/models/__init__.py` (`AbstractModelBuilder` added to imports + `__all__`). Matches the hard requirement in the Red-team adjustment (public-surface `explanation.models`, B1-tolerable).
conacq import is `from explanation.models.abstract_model_builder import AbstractModelBuilder` — module path, no leading-underscore module or symbol, no deep-private leak. The other `from explanation.models.*` imports in congen builder (`task_preparation`, `testsuite`) are pre-existing; **no new boundary crossing class introduced.**

### 5. No caller regression — PASS
All builder call sites still resolve: `ConGenModelBuilder.from_bias().with_oracle().with_examples().build()` (test_congen, congen_runner), `QuAcqModelBuilder.from_bias().with_oracle().build()` (test_quacq, quacq_runner), `DiagnosisModelBuilder.from_*().with_negation()/.for_redundancy().build()` (test_diagnosis ×36, test_executor, test_assumption_slicer). Suite green confirms.

## Findings by severity

### Low
- **L1 — Dead import.** `explanation/models/abstract_model_builder.py:18` imports `abstractmethod` from `abc`, but it is never used (hooks are concrete defaults using `raise NotImplementedError` / no-op, not `@abstractmethod`). AST + manual scan confirm zero usage. ruff/pyflakes would flag F401.
  - **Why intentional-looking:** the hooks deliberately are *not* abstract (so Diagnosis isn't forced to implement them) — see review point 3. So `abstractmethod` was imported in anticipation but correctly not applied.
  - **Fix:** `from abc import ABC` (drop `abstractmethod`). 1-line, non-blocking.

### Informational (non-blocking, no action required for A2)
- **I1 — `last_task` side-channel** deliberately retained on the 2 concrete builders with `# B4 removes this side-channel` markers. Correctly out of A2 scope per spec. Note: the comment references "B4" (a plan-stage label) in code — see global rule "no plan references in code comments." Borderline since "B4" is a future-stage marker, not an invariant. Recommend rephrasing to intent-only (e.g. `# transient build output; slated for removal once callers read the task directly`) when B4 lands. Not an A2 defect.
- **I2 — `with_negation` is a documented no-op for ConGen/QuAcq** (base docstring lines 64-71). Negation for those is always oracle-driven at build; the flag is kept "for uniform fluent API." Mild YAGNI smell but harmless and explicitly documented; keeping the API uniform across 3 builders is defensible. No change.
- **I3 — `for_redundancy = AbstractModelBuilder.with_negation`** (diagnosis_model_builder.py:104): correct. Assigning the base's plain function as a class attr keeps normal `self`-binding (identical semantics to the old `for_redundancy = with_negation`). Verified suite-green.

## Positive observations
- Clean line-for-line extraction; the negation block now has a single source of truth.
- Hooks-not-abstractmethods is the right call for the asymmetric Diagnosis case — avoids forcing meaningless stubs (genuine KISS).
- Explicit, accurate docstrings on the base explain *why* Diagnosis overrides `build()` and why the flag is a no-op for ConGen/QuAcq.
- Boundary handled exactly per the Red-team-pinned location; B1 will only need to fold into `api.py`, no relocation.

## Recommended actions
1. (Low, optional) Drop unused `abstractmethod` import — `explanation/models/abstract_model_builder.py:18`.
2. (Defer to B4) Rephrase `# B4 removes this side-channel` comments to intent-only when that stage lands.

## Metrics
- Tests: 376 passed / 0 failed / 1 known warning (baseline matched).
- Type hints: present on all public methods; base uses `Any` return for `build()`/hooks (acceptable — heterogeneous model types).
- Net LOC: -72 (DRY).
- Lint: ruff unavailable in env; AST confirms single F401 (L1).

## Unresolved questions
- None blocking. Only open item is the cosmetic L1 dead import (safe to fix now or leave for a lint sweep).
