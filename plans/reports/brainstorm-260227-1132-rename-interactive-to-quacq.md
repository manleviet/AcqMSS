# Brainstorm: Rename interactive → QuAcq + Add Example Modes

## Problem Statement

1. `run_interactive.py` only supports oracle modes (`automated`/`interactive`), not example-based modes (`example_only`/`example_first`)
2. "Interactive" naming is generic — should be "QuAcq" to match the algorithm
3. Full rename across package, runners, app, config, tests, docs

## Current State

### Files in scope (~15 .py files + 2 TOML + 9 docs)

**Package: `conacq/algorithms/interactive/`** (folder rename → `quacq/`)
| Current | Proposed |
|---|---|
| `interactive_model.py` → `InteractiveModel` | `quacq_model.py` → `QuAcqModel` |
| `interactive_task_preparation.py` | `quacq_task_preparation.py` |
| `quacq_task.py` | stays (already named correctly) |
| `task.py` → `DiagnosisTask` | stays (generic, not "interactive") |
| `learner.py` → `Learner` | stays (generic) |
| `quacq.py` → `QuAcq` | stays (already named correctly) |
| `findc.py` → `FindC` | stays (algorithm name) |
| `findscope.py` → `FindScope` | stays (algorithm name) |
| `_task_compat.py` | stays (internal compat) |

**Runner:**
| Current | Proposed |
|---|---|
| `interactive_runner.py` | `quacq_runner.py` |
| `InteractiveRunner` | `QuAcqRunner` |
| `InteractiveRunResult` | `QuAcqRunResult` |

**App + Config:**
| Current | Proposed |
|---|---|
| `apps/run_interactive.py` | `apps/run_quacq.py` |
| `apps/conf/run_interactive_config.toml` | `apps/conf/run_quacq_config.toml` |
| `tests/test_interactive.py` | `tests/test_quacq.py` |

**Consumers (import updates only):**
- `conacq/runners/__init__.py`
- `conacq/algorithms/__init__.py`
- `conacq/algorithms/acqmss/__init__.py`
- `conacq/eval/cross_validation.py`
- `conacq/eval/progressive_evaluation.py`
- `conacq/eval/__init__.py`
- `conacq/examples/query_converter.py`
- `apps/run_evaluation.py`

**Docs (text updates):** 9 files in `docs/`

## Adding Example Modes to run_quacq.py

### Example Source Pattern

Following `run_congen.py` established pattern:
- `ModelConfig.examples` field already exists (optional)
- `ExampleIO.load_json()` already handles JSON loading
- TOML: add `examples = "path/to/examples.json"` to `[[models]]` section
- When `mode` is `example_only`/`example_first` and `examples` is provided → load and pass to runner

### Mode Dispatch Logic

```
mode = config or CLI arg
if mode in ('automated', 'interactive'):
    runner.run(mode=mode)  # oracle path, no examples needed
elif mode in ('example_only', 'example_first'):
    require model_config.examples
    load examples via ExampleIO
    runner.run(pos, neg, mode=mode)  # example path
```

### TOML Config Changes

```toml
[quacq]
max_queries = 1000
mode = "example_only"  # automated | interactive | example_only | example_first
solver_name = "glucose4"

[[models]]
name = "REAL-FM-7"
oracle = "data/fms/REAL-FM-7.uvl"
bias = "data/bias/REAL-FM-7-bias.json"
examples = "data/examples/REAL-FM-7_rs_1n.json"  # required for example modes
```

## Recommended Approach

### Phase 1: Package Rename (high blast radius, do first)
1. Rename folder `conacq/algorithms/interactive/` → `conacq/algorithms/quacq/`
2. Rename files: `interactive_model.py` → `quacq_model.py`, `interactive_task_preparation.py` → `quacq_task_preparation.py`
3. Rename classes: `InteractiveModel` → `QuAcqModel`
4. Update all imports across codebase
5. Run tests to verify

### Phase 2: Runner Rename
1. Rename `interactive_runner.py` → `quacq_runner.py`
2. Rename classes: `InteractiveRunner` → `QuAcqRunner`, `InteractiveRunResult` → `QuAcqRunResult`
3. Update all consumers
4. Run tests

### Phase 3: App + Config + Tests
1. Rename `run_interactive.py` → `run_quacq.py`
2. Rename config TOML
3. Add example loading + mode dispatch
4. Rename `test_interactive.py` → `test_quacq.py`
5. Update TOML section `[interactive]` → `[quacq]`

### Phase 4: Docs Update
1. Update all 9 docs files
2. Update CLAUDE.md if needed

## Risks

| Risk | Mitigation |
|---|---|
| Git loses file history on rename | Use `git mv` for each file |
| `__pycache__` stale bytecode | Delete old `__pycache__` dirs |
| Import chain breakage | Run tests after each phase |
| `interactive` mode string (oracle) confused with old package name | Mode string `'interactive'` stays — it describes oracle UX, not algorithm |

## Key Decision: Keep `interactive` as mode string

The oracle mode `'interactive'` (human answers queries) is NOT being renamed. It describes a UX mode, not the algorithm. Only package/class/file names change. The 4 mode strings stay: `automated`, `interactive`, `example_only`, `example_first`.

## Success Criteria

- All 4 modes work in `run_quacq.py`
- All tests pass after rename
- No import errors
- Docs consistent
- Git history preserved via `git mv`
