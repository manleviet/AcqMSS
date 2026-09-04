# Code Review — B4: Builder statelessness + FMOracle purity

**Date:** 2026-06-21
**Branch:** feat/redesign-abc (uncommitted working tree only)
**Scope:** `git diff` — 11 files, +152/-116. Highest-regression-risk stage (oracle correctness path).
**Spec:** plans/260621-1416-redesign-abc/phase-10-b4-builder-statelessness-fmoracle-purity.md (FULL RESTRUCTURE, no model round-trip).
**Tests:** `uv run --no-sync pytest tests/ -q` → **468 passed, 1 warning** (known `TestSuiteReader` PytestCollectionWarning). No flaky failure this run.

## VERDICT: PASS

Both parts are correct and behavior-preserving. Empirically verified byte-identical codec maps / base_set_c / bg_data between HEAD and working tree on REAL-FM-7 + arcade-game; `complete_configuration` round-trips valid; purity holds; lazy `_bg_data` cache is idempotent and config-independent. Only minor (non-blocking) items below.

---

## CRITICAL VERIFICATION VERDICTS

### (1) No assertion dropped (PART 1) — VERDICT: PASS (zero lost coverage)

Each old `builder.last_task` assertion has an equivalent (or stronger) assertion on the explicit `prepare_task()` return. Mapping:

| Test | Old (HEAD) | New (working tree) | Status |
|------|-----------|--------------------|--------|
| `test_congen.py::test_auto_prepare_from_file` | `assert builder.last_task is not None` + `len(builder.last_task.set_kb) > 0` | `assert task is not None` + `len(task.set_kb) > 0` (task = prepare_task return) | EQUIVALENT |
| `test_congen.py::test_auto_prepare_from_data` | `assert builder.last_task is not None` | `assert task is not None` | EQUIVALENT |
| `test_congen.py::test_last_call_wins` | `assert builder.last_task is not None` | `assert task is not None` via `get_examples()`→raw data | EQUIVALENT (now exercises last-call-wins through `get_examples`, slightly stronger) |
| `test_congen.py::test_cv_re_prepare` | already explicit `prepare_task` in HEAD | unchanged | PRESERVED |
| `test_quacq.py` fixture `interactive_model` | `task = builder.last_task` | `task = model.prepare_task(oracle)` | EQUIVALENT |
| `test_quacq.py:250` (integration) | `task = builder.last_task` | `task = model.prepare_task(oracle)` | EQUIVALENT |
| `test_quacq.py::test_prepare_task_returns_task` | `task = builder.last_task` + `is not None` + `isinstance QuAcqTask` | `task = model.prepare_task(oracle)` + same asserts | EQUIVALENT |
| `test_assumption_slicer.py` `congen_task` fixture | `builder.build(); return builder.last_task` | `model=build(); pos,neg=get_examples(); return prepare_task(...)` | EQUIVALENT (downstream set_b/assumptions asserts unchanged) |
| `test_assumption_slicer.py` `quacq_task` fixture | `return builder.last_task` | `return model.prepare_task(oracle)` | EQUIVALENT |
| `test_assumption_slicer.py` Site-5 (×5 base_set_c) | `model._base_set_c[...]` | `task = model.prepare_task(); task.base_set_c[...]` | EQUIVALENT — same computed value (verified byte-identical), now tests the new contract |
| `test_assumption_slicer.py` integration (×2) | `task = builder.last_task; task.set_b == [156]/[28]` | `task = prepare_task(...); task.set_b == [156]/[28]` | EQUIVALENT |
| `test_oracle_model.py` (×4) | `list(model._base_set_c)` | `list(task.base_set_c)` | EQUIVALENT — same value |

No assertion weakened or deleted. `neg or []` semantics preserved (`get_examples()`→`_resolve_examples()` already returns `neg or []`).

### (2) FMOracle purity behavior-preserving (PART 2) — VERDICT: PASS

**(a) No model mutation in `prepare()`.** Grep `model.X =` inside `fm_oracle_model.py` → **0 matches**. The static `prepare()` (lines 173-260) writes nothing onto the passed-in model. Old back-writes (`model._pos_assignment_to_assumption`, `model._neg_assignment_to_assumption`, `model._base_set_c`, `model._bg_data`) all removed; the orphan class-level type stubs (`_pos/_neg/_base_set_c`) are deleted too. Empirically confirmed: after `build()` + multiple `prepare_task()`, `hasattr(model, "_base_set_c"/"_pos_assignment_to_assumption"/"_neg_assignment_to_assumption")` is all False.

**(b) 4 maps flow prepare→_FMPrepResult→codec correctly — same values.** Computation is byte-identical to HEAD (diffed line-by-line; only the assignment targets changed). Empirically diffed working-tree vs HEAD on REAL-FM-7 — identical:
- `base_set_c = [28,30,...,54]` (14 IDs) — identical
- `pos_assignment_to_assumption` (14 entries) — identical
- `neg_assignment_to_assumption` (14 entries) — identical
- `bg_data.assumptions=(28,29)`, `next_available_id=84` — identical

**(c) `model_to_config`/`complete_configuration`/`is_valid` byte-identical behavior.** `_model_to_config` line unchanged (`self._base_task.codec.model_to_config(model)`). `is_valid` only re-pointed `base_set_c` source (model→`_base_task.base_set_c`) — same value. `complete_configuration` unchanged except it consumes the same codec. Empirically: `complete_configuration({root: True})` returns a config that `is_valid()` accepts on both REAL-FM-7 and arcade-game.

**(d) Lazy `_bg_data` idempotency analysis — SAFE.** See dedicated section below.

### (3) Ordering cycle resolved — VERDICT: PASS

The `prepare()→model→codec` read-back cycle is eliminated. `prepare()` returns `_FMPrepResult`; `prepare_task()` builds the codec directly from `prep.pos_assignment_to_assumption` / `prep.neg_assignment_to_assumption` (fm_oracle_model.py:100-104) — never reads back from model attributes. No model round-trip remains.

### (4) Interaction with prior codec fix — VERDICT: PASS

The committed `_model_to_config` delegation to `self._base_task.codec.model_to_config(...)` is left UNCHANGED (fm_oracle.py:179). Codec remains a single source: `self._base_task.codec`, built once in `prepare_task`. `is_valid` reads `self._base_task.codec` (line 104) — same task, same codec. Consistent.

### (5) No silent format/contract change to Task — VERDICT: PASS (with one minor note)

`task.base_set_c` is the only new attribute; attached dynamically. Nothing else on `Task`/`DiagnosisTask` changed. `last_task` grep is clean across conacq/explanation/apps/tests (0 hits). No plan-stage labels in code/comments. Conacq-scoped. See Low-1 re: dynamic-attr consistency.

---

## LAZY `_bg_data` IDEMPOTENCY ANALYSIS (Critical-path)

**Question:** Could two `prepare_task` calls with different inputs corrupt a shared cached `_bg_data` (CV re-prepare)?

**Answer: No. The cache is safe.** Reasoning:

1. **Guard is set-once:** `prepare_task` does `if self._bg_data is None: self._bg_data = prep.bg_data` (fm_oracle_model.py:113-114). After the first set (which always happens inside `build()` → line 152, no config), every subsequent `prepare_task` skips the assignment. The cached object is never replaced.

2. **`bg_data` is configuration-independent.** In `prepare()`, `bg_data` is built (lines 240-252) from `result.set_kb[:2]`, `result.assumptions[0:2]`, `id_assumption`, `assignment_clauses`, `assignment_assumptions`, and the pos/neg maps — none of which depend on `configuration`. The `configuration` argument only affects `result.set_c` (Step 3b, lines 224-233), computed separately and NOT fed into `bg_data`. So even if the first `prepare_task` had carried a configuration, the cached `bg_data` would be identical to the no-config one. No corruption is possible from a configured re-prepare.

3. **First setter is always the no-config base.** `build()` calls `prepare_task()` (no args) before any caller can pass a configuration, so the cache is seeded from the canonical base task.

4. **`prepare()` recomputes a fresh `bg_data` per call but discards it** when the cache is already set — no shared-mutable aliasing between calls (each `prepare` builds new dicts via `dict(pos_...)`).

**Empirical confirmation:** Called `prepare_task({root: True})` AFTER build on both FMs; `get_bg_data()` returned the SAME object identity (`bg1 is bg2` True) with unchanged `assumptions` — the configured re-prepare did not replace or mutate the cache.

**Hot-path safety:** `is_valid`/`complete_configuration` never call `prepare_task`, so the query path never touches the cache.

---

## FINDINGS BY SEVERITY

### Critical — none.

### High — none.

### Medium — none.

### Low

- **Low-1 — `task.base_set_c` is a dynamically-attached attribute, not a declared `Task` field.**
  `fm_oracle_model.py:109` (`task.base_set_c = prep.base_set_c  # type: ignore[attr-defined]`), read at `fm_oracle.py:107,193`. `Task` is a `@dataclass` with no `__slots__`, so runtime attachment works (same mechanism as `codec`/`describe`). But unlike `codec`/`describe`, `base_set_c` is NOT declared as a dataclass field — hence the `# type: ignore`. This is the only oracle-specific extension and it's harmless today, but a declared `Optional[List[int]]` field on `Task` (or a typed subclass) would drop the 3 `type: ignore` pragmas and make the contract self-documenting. Non-blocking; YAGNI-acceptable to defer.
  **Fix (optional):** add `base_set_c: Optional[List] = field(default_factory=list)` to `Task` (or to `DiagnosisTask`), remove the 3 `# type: ignore[attr-defined]`.

- **Low-2 — stale `_base_set_c` references in test comments.**
  `tests/test_assumption_slicer.py:13` and `:397` still say `FMOracleModel._base_set_c` in the "Site 5" docstring/section banner, though the attribute no longer exists (now `task.base_set_c`). The test bodies were updated; only the comments lag. Cosmetic.
  **Fix (optional):** update both comment lines to `task.base_set_c (FMOracleTaskPreparation)`.

### Informational

- `bg_data` property docstring updated to "Call build() (or prepare_task()) first" — accurate; the `RuntimeError` message still says "Call prepare_task() first" (fm_oracle_model.py:74). Minor wording mismatch, harmless.
- `FMOracleModel` class docstring still says "Immutable KB container" while `build()` legitimately populates `constraint_map`/`variables`/`next_available_id`. "Immutable" refers to per-task state, not construction; acceptable.

---

## POSITIVE OBSERVATIONS

- Clean elimination of the `prepare()→model→codec` cycle via `_FMPrepResult` — exactly the FULL RESTRUCTURE the Validate decision mandated; no model-write-then-copy fallback left.
- `_FMPrepResult` is a focused internal dataclass with a clear docstring explaining why it exists.
- Purity is real and verifiable by grep (`model.X =` → 0 in prepare).
- PART 1 test migration genuinely strengthens several tests (asserts now run on the actual returned task + exercise `get_examples()` resolution).
- bg_data set-once guard + config-independence is the correct minimal design for CV re-prepare safety.
- `last_task` fully removed everywhere including apps/ and docstrings; no orphaned readers.

---

## METRICS

- Tests: 468 passed / 0 failed / 1 known warning.
- `last_task` references: 0 (clean).
- Stale model-attr references in production code: 0.
- Type-safety pragmas added: 3 × `# type: ignore[attr-defined]` (all for `base_set_c`; see Low-1).
- Behavior diff vs HEAD on oracle path: byte-identical (REAL-FM-7 + arcade-game, codec maps + base_set_c + bg_data).

## Unresolved Questions

None. All five critical verifications pass. Low-1/Low-2 are optional polish, non-blocking for commit.

**Status:** DONE
