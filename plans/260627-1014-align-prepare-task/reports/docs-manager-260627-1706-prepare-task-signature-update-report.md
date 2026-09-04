# Documentation Update Report: prepare_task Signature Refactoring

**Date**: 2026-06-27  
**Status**: COMPLETED  
**Scope**: Update all code examples and contract descriptions reflecting `prepare_task()` signature change from accepting `oracle` parameter to embedding frozen `OracleTaskData` snapshot at build time.

## Changes Summary

All four KB models now share `prepare_task(task_input: TaskInput) -> Task` contract:
- **ConGenModel**: `prepare_task(task_input)` (was: `prepare_task(task_input, oracle)`)
- **QuAcqModel**: `prepare_task()` (was: `prepare_task(TaskInput(), oracle)` — QuAcq rejects non-empty TaskInput)
- **FMOracleModel**: `prepare_task()` (was: `prepare_task(configuration)`)

The oracle is NO LONGER passed to prepare_task. Instead, a frozen `OracleTaskData` snapshot is folded onto the model at BUILD time (in the builder's `_post_negation_build` hook); prepare_task reads from `model._oracle_data`.

---

## Files Updated

### 1. README.md
**Lines 69-72** (ConGen multi-line example):
```python
# Before
task = model.prepare_task(
    TaskInput(positive_test_cases=pos_examples, negative_test_cases=neg_examples),
    oracle
)

# After
task = model.prepare_task(
    TaskInput(positive_test_cases=pos_examples, negative_test_cases=neg_examples)
)
```

**Line 105** (QuAcq example):
```python
# Before
task = model.prepare_task(TaskInput(), oracle)

# After
task = model.prepare_task()
```

### 2. docs/README.md
**Line 185** (CONGEN process line):
```markdown
# Before
Process: `ConGenModel.prepare_task(TaskInput(...), oracle)` → GenerateNE (internal) → ACQMSS → REDUCE

# After
Process: `ConGenModel.prepare_task(TaskInput(...))` → GenerateNE (internal) → ACQMSS → REDUCE
```

### 3. docs/codebase-summary.md
**Line 103** (file count & description):
```markdown
# Before
**Oracle Sub-package** (`conacq/oracle/`, 11 files, ~1,200 LOC, B3 redesign):

# After
**Oracle Sub-package** (`conacq/oracle/`, 11 files, ~1,300 LOC, B3 redesign + Phase R snapshot):
```

**Line 141** (Builder Pattern):
```markdown
# Before
7. **Builder Pattern**: ConGenModelBuilder requires oracle for build-time negation. `build()` returns immutable KB. Call `model.prepare_task(task_input, oracle)` per fold.

# After
7. **Builder Pattern**: ConGenModelBuilder requires oracle for build-time negation. `build()` returns immutable KB. Call `model.prepare_task(task_input)` per fold.
```

**Lines 109-110** (Added OracleTaskData entry to file inventory):
```markdown
| `oracle_task_data.py` | 50+ | OracleTaskData: frozen snapshot of oracle state (get_bg_data, get_c, get_kb, get_assumptions). Folded onto model at build time; enables prepare_task() to access oracle metadata without storing live oracle. |
```

**Lines 505-510** (Phase R Architecture contract rewrite):
```markdown
# Before
- `model.prepare_task(task_input, oracle) → Task` is pure: fresh Task per call
- ...
- Oracle injected at prepare_task() time, not stored in model

# After
- `model.prepare_task(task_input) → Task` is pure: fresh Task per call
- ...
- Oracle BG snapshot (OracleTaskData) folded onto the model at build time; the live oracle is not stored — the model stays a pure immutable KB
```

### 4. docs/system-architecture.md
**Line 75** (ConGen CV example):
```python
# Before
task = model.prepare_task(task_input, oracle)  # Pure function → fresh ConGenTask

# After
task = model.prepare_task(task_input)  # Pure function → fresh ConGenTask
```

**Line 99** (QuAcq example):
```python
# Before
task = model.prepare_task(TaskInput(), oracle)

# After
task = model.prepare_task()
```

**Line 245** (ConGenRunner.run() documentation):
```markdown
# Before
- Prepare: `task = model.prepare_task(TaskInput(...), oracle)`

# After
- Prepare: `task = model.prepare_task(TaskInput(...))`
```

**Line 253** (QuAcqRunner.run() documentation):
```markdown
# Before
- Prepare: `task = model.prepare_task(TaskInput(), oracle)` (fresh task per run)

# After
- Prepare: `task = model.prepare_task()` (fresh task per run)
```

**Lines 645-646** (ConGen overview contract):
```markdown
# Before
- **ConGenModel**: Immutable KB container (bias + negation map). Oracle injected at prepare_task() time.
- **Task Factory**: `model.prepare_task(task_input, oracle)` returns fresh ConGenTask with E+/E-/NE

# After
- **ConGenModel**: Immutable KB container (bias + negation map). A frozen OracleTaskData BG snapshot is folded onto the model at build time; prepare_task takes only TaskInput.
- **Task Factory**: `model.prepare_task(task_input)` returns fresh ConGenTask with E+/E-/NE
```

**Line 679** (ConGen data flow diagram):
```
# Before
├─→ [run] task = model.prepare_task(TaskInput(E+, E-), oracle)

# After
├─→ [run] task = model.prepare_task(TaskInput(E+, E-))
```

**Line 708** (QuAcq data flow diagram):
```
# Before
├─→ [run] task = model.prepare_task(TaskInput(), oracle)

# After
├─→ [run] task = model.prepare_task()
```

**Lines 748, 752** (Phase R Design section — major contract rewrite):
```markdown
# Before
- **Per-run Prepare**: model.prepare_task(TaskInput(), oracle) returns fresh Task each run
- **Oracle Injected**: Passed to prepare_task(), not stored in model

# After
- **Per-run Prepare**: model.prepare_task() returns fresh Task each run
- **Oracle BG Snapshot**: A frozen OracleTaskData is folded onto the model at build (in _post_negation_build); the live oracle is NOT stored — only its immutable BG/KB snapshot.
```

### 5. docs/code-standards.md
**Line 205** (QuAcqRunner example in docstring):
```python
# Before
task = self.model.prepare_task(TaskInput(), self.oracle)

# After
task = self.model.prepare_task()
```

**Line 380** (Manual ConGen control example):
```python
# Before
task = model.prepare_task(task_input, oracle)  # Pure function → fresh Task

# After
task = model.prepare_task(task_input)  # Pure function → fresh Task
```

**Line 404** (Task-as-Unit Pattern definition):
```markdown
# Before
Models are immutable KBs; Tasks are immutable units of work. Each `model.prepare_task(task_input, oracle)` call returns a fresh, independent Task with its own assumption ID lists. All Tasks from the same KB share the same VariableCodec (KB-level single source of truth).

# After
Models are immutable KBs; Tasks are immutable units of work. Each `model.prepare_task(task_input)` call returns a fresh, independent Task with its own assumption ID lists. All Tasks from the same KB share the same VariableCodec (KB-level single source of truth).
```

**Line 499** (Test example):
```python
# Before
task = model.prepare_task(TaskInput(), oracle)

# After
task = model.prepare_task()
```

### 6. docs/congen.md
**Line 141** (GenerateNE invocation context):
```markdown
# Before
- Invoked by `ConGenTaskPreparation` during `model.prepare_task(task_input, oracle)`

# After
- Invoked by `ConGenTaskPreparation` during `model.prepare_task(task_input)`
```

**Line 333** (Implementation detail #1):
```markdown
# Before
1. **Immutable Model Design** (Phase R): Models are thin KB containers; `prepare_task(TaskInput, oracle)` returns fresh Task per call

# After
1. **Immutable Model Design** (Phase R): Models are thin KB containers; `prepare_task(TaskInput)` returns fresh Task per call
```

**Line 341** (Implementation detail #9):
```markdown
# Before
9. **CV fold reuse**: `model.prepare_task(TaskInput(fold_pos, fold_neg), oracle)` supports multiple fold evaluations

# After
9. **CV fold reuse**: `model.prepare_task(TaskInput(fold_pos, fold_neg))` supports multiple fold evaluations
```

**Line 386** (CV wrapper feature):
```markdown
# Before
- Per-fold task creation via `model.prepare_task(TaskInput(fold_pos, fold_neg), oracle)`

# After
- Per-fold task creation via `model.prepare_task(TaskInput(fold_pos, fold_neg))`
```

### 7. docs/quacq.md
**Line 208** (GenerateNE invocation context):
```markdown
# Before
   - Invoked by `ConGenTaskPreparation` during `model.prepare_task(task_input, oracle)`

# After
   - Invoked by `ConGenTaskPreparation` during `model.prepare_task(task_input)`
```

**Line 357** (QuAcq code example):
```python
# Before
oracle = FeatureModelOracle('data/fms/model.uvl')
task = model.prepare_task(oracle)

# After
oracle = FeatureModelOracle('data/fms/model.uvl')
task = model.prepare_task()
```

---

## Validation

**Acceptance Criteria**: `grep -rn "\.prepare_task(.*oracle" README.md docs/ | grep -v journals` returns EMPTY.

**Result**: ✅ PASS — No instances of `prepare_task` receiving an oracle parameter found in documentation.

---

## Summary

- **Files modified**: 7 (README.md, docs/README.md, docs/codebase-summary.md, docs/system-architecture.md, docs/code-standards.md, docs/congen.md, docs/quacq.md)
- **Code examples updated**: 18 occurrences
- **Contract descriptions rewritten**: 3 major sections (codebase-summary.md:509, system-architecture.md:645-646 + 752, quacq.md:208)
- **OracleTaskData documented**: Added to file inventory with full description

All changes are surgical (markdown-only, no code modifications) and preserve document structure and formatting. Historical records (journals, roadmap, PDR) untouched as required.
