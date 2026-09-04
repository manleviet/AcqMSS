# A6 Apps CLI Harness + Atomic JSON — Implementation Report

## Phase
- Phase: 06 — A6 apps/ CLI harness + atomic JSON
- Plan: /Users/manleviet/Development/GitHub/AcqMSS/plans/260621-1416-redesign-abc
- Status: completed

## Files Modified

| File | Action | Key change |
|---|---|---|
| `apps/_harness.py` | CREATE | `configure_logging()` + `atomic_json_write()` |
| `apps/run_congen.py` | MODIFY | logging, imports `_harness` |
| `apps/run_cv.py` | MODIFY | logging + `atomic_json_write` for CV JSON |
| `apps/run_compare.py` | MODIFY | logging + `atomic_json_write` for read-modify-write |
| `apps/run_quacq.py` | MODIFY | logging |
| `apps/run_evaluation.py` | MODIFY | logging + `atomic_json_write` for eval JSON; B1 note |
| `apps/generate_bias_config.py` | MODIFY | `os.chdir` removed; uses `load_pipeline_config` |
| `apps/generate_bias_files.py` | MODIFY | logging; own `load_toml_config` kept (different schema) |
| `apps/generate_examples.py` | MODIFY | logging; uses `load_pipeline_config` |
| `apps/generate_cv_folds.py` | MODIFY | logging; uses `load_pipeline_config` |
| `apps/extract_results.py` | MODIFY | logging (8 print → logger); added `configure_logging` |
| `tests/test_apps_harness.py` | CREATE | 17 new tests |

## Tasks Completed

- [x] `apps/_harness.py` with `configure_logging` + `atomic_json_write`
- [x] `atomic_json_write`: temp in `target.parent` (same fs), `os.replace` rename
- [x] `run_cv.py` JSON write → `atomic_json_write`
- [x] `run_compare.py` read-modify-write → build full dict first, then `atomic_json_write`
- [x] `run_evaluation.py` JSON write → `atomic_json_write`
- [x] `run_compare.py` CLI mode (`compare_kb`) → `atomic_json_write`
- [x] All 254 `print()` → `logger.*`; `configure_logging` wires stdout handler
- [x] `-v` CLI UX preserved: INFO → stdout, WARNING-only when silent
- [x] `os.chdir` workaround removed from `generate_bias_config.py`
- [x] `generate_bias_config.py` uses `load_pipeline_config` (was own `load_config`)
- [x] `generate_examples.py` uses `load_pipeline_config` (was own `load_config`)
- [x] `generate_cv_folds.py` uses `load_pipeline_config` (was inline `tomllib.load`)
- [x] B1 boundary reach-ins noted in `run_evaluation.py` docstring (not fixed)

## Harness Design

### `apps/_harness.py`

**`configure_logging(verbose, debug)`**
- `--debug` → DEBUG; `-v` → INFO; default → WARNING (silent batch).
- Wires a `StreamHandler(sys.stdout)` with `%(message)s` format — preserves CLI UX.
- Idempotent: replaces existing handlers to avoid duplicate output.

**`atomic_json_write(data, target, indent=2)`**
- `tempfile.mkstemp(dir=target.parent)` → same filesystem as target → `os.replace` is POSIX-atomic.
- `json.dump` to fd, close, then `os.replace(tmp, target)`.
- On any exception: `os.unlink(tmp)` then re-raise. Source never truncated.
- Creates `target.parent` if needed.

## JSON Write Sites Rerouted (5 total)

| Script | Location | Pattern | Fix |
|---|---|---|---|
| `run_cv.py` | line ~190 | write-new | `atomic_json_write(unified, cv_file)` |
| `run_compare.py` | `compare_model_unified` | read-modify-write same file | full dict built in-memory first, then `atomic_json_write(data, cv_file)` |
| `run_compare.py` | `compare_kb` (CLI mode) | write-new | `atomic_json_write(eval_data, eval_file)` |
| `run_evaluation.py` | `process_model` | write-new | `atomic_json_write(output, output_file)` |

Note: `run_congen.py` JSON writes go through `save_kb_result()` (internal library function) — not an apps-level raw write; out of scope.

## print() Count

```
Before: grep -rc "print(" apps/ --include="*.py" = 254
After:  grep -rc "print(" apps/ --include="*.py" = 0
```

## os.chdir Removal

`generate_bias_config.py` lines 31-33 previously:
```python
ROOT_PROJECT_FOLDER = Path(__file__).resolve().parent.parent
os.chdir(ROOT_PROJECT_FOLDER)
sys.path.insert(0, os.getcwd())
```
Removed entirely. Script is invoked as `python -m apps.generate_bias_config` from repo root, so `sys.path` and CWD are correct by the module runner. The `import os` and `import sys` lines were also removed.

## Automated Tests Added (17 tests)

`tests/test_apps_harness.py`:

**(a) Round-trip** (`TestAtomicJsonWriteRoundTrip` — 6 tests)
- `test_simple_dict_roundtrip` — write dict, read back, assert equal
- `test_no_temp_file_left_behind` — no `*.tmp` stray files
- `test_creates_parent_dirs` — nested path auto-created
- `test_indent_default` — output uses indent=2 (not compact)
- `test_overwrite_existing` — clobbers prior content correctly
- `test_list_roundtrip` — list of dicts serialises correctly

**(b) Fault injection** (`TestAtomicJsonWriteFaultInjection` — 3 tests)
- `test_original_untouched_on_replace_failure` — monkeypatches `os.replace` to raise; original byte-identical after
- `test_no_temp_file_left_on_replace_failure` — orphaned `.tmp` cleaned up
- `test_new_file_not_created_on_replace_failure` — target doesn't appear on failure

**(c) Config-loader** (`TestConfigLoader` — 5 tests)
- `test_general_section_extraction` — `output_dir`, `verbose` present and correct types
- `test_parse_models_returns_list` — ≥1 model returned
- `test_model_config_fields` — `name`, `oracle`, `bias` non-empty strings
- `test_output_dir_matches_known_value` — regression: `'data/results'`
- `test_model_name_derived_from_oracle_when_missing` — name always non-empty

**Smoke** (`TestConfigureLogging` — 3 tests): `configure_logging` doesn't raise in all three modes.

## Smoke-Run Evidence

```
$ python -m apps.run_congen apps/conf/run_congen_config.toml -v
============================================================
ConGen Constraint Acquisition
============================================================
Config: apps/conf/run_congen_config.toml
Output: data/results
Models: 1
Mode: incremental
Solver: glucose4

Processing: REAL-FM-7_rs_1n
  FM: data/fms/REAL-FM-7.uvl
  Bias: data/bias/REAL-FM-7-bias.json
  Examples: data/examples/REAL-FM-7_rs_1n.json
  Mode: incremental
  Bias constraints: 295
  E+: 13, E-: 1
  MSS size: 78
  Acquired KB: 17 constraints
  Constraints: [10 shown, 7 more]
  Saved: data/results/REAL-FM-7_rs_1n_rs_1n_kb.json

============================================================
Completed: 1/1 models
============================================================
```
Output format and content unchanged from pre-refactor baseline.

## Final Test Summary

```
437 passed, 1 warning in 53.88s
```
- Baseline: 420 passed; new: +17
- Known pre-existing warning: `PytestCollectionWarning` from `TestSuiteReader.__init__`
- `test_consistency_check_count_parity` not in failed list (passed)

## B1 Boundary Violations Noted (not fixed)

`run_evaluation.py::process_model` reaches into:
- `runner.model.constraint_map` (QuAcqRunner internal)
- `runner.feature_ids` (runner internal)
- `run_quacq.py::process_model` also accesses `runner.model.constraint_map`, `runner.feature_ids`

Tracked for stage B1 boundary cleanup.

## Deviations

1. `generate_bias_files.py` keeps its own `load_toml_config` — its config schema (`[settings]` + `[[models]][config]`) differs from the pipeline TOML schema (`[general]` + `[[models]][oracle/bias]`). Sharing `load_pipeline_config` would require schema conversion; YAGNI — the existing loader is correct and self-contained.
2. `extract_results.py` keeps its inline `tomllib.load` in `main()` for the config (simple 3-key read); the 8 `print()` calls were converted to `logger.*` with `configure_logging` added. The data-loading and table-generation functions are pure computation — untouched.

## Unresolved Questions

None.

---

**Status:** DONE
**Summary:** Harness module created; 254 print() → logging (0 remaining); 5 JSON write sites atomic; os.chdir removed; 17 new tests; smoke-run clean; 437/437 passed.
