# Code Review — Stage A6: apps/ CLI harness + atomic CV-JSON + print→logging

Date: 2026-06-21
Scope: uncommitted working-tree changes only (`git diff` + new `apps/_harness.py`, `tests/test_apps_harness.py`)
Branch: feat/redesign-abc
Verdict: **PASS**

## Scope reviewed
- New: `apps/_harness.py`, `tests/test_apps_harness.py`
- Modified: `apps/run_cv.py`, `apps/run_compare.py`, `apps/run_evaluation.py`, `apps/run_congen.py`, `apps/run_quacq.py`, `apps/generate_bias_config.py`, `apps/generate_bias_files.py`, `apps/generate_examples.py`, `apps/generate_cv_folds.py`, `apps/extract_results.py`
- LOC: ~435 changed across 11 files

## Test result
- `uv run --no-sync pytest tests/ -q` → 436 passed, 1 failed, 1 warning.
- Sole failure = `test_consistency_check_count_parity` (the known flake; passes in isolation: re-ran → 1 passed). Not A6-related (parallel/serial consistency-check counting). Effective: **437 passed**.
- `tests/test_apps_harness.py` → 17 passed.

---

## EXPLICIT VERDICTS (the two highest-risk questions)

### (1) Byte-identical on-disk CV-JSON vs OLD writes — VERIFIED IDENTICAL
- All four old inline call sites used EXACTLY `json.dump(..., indent=2)` with no other kwargs:
  - `run_cv.py:193` `json.dump(unified, f, indent=2)`
  - `run_compare.py:152` `json.dump(data, f, indent=2)` (config-mode read-modify-write)
  - `run_compare.py:212` `json.dump(eval_data, f, indent=2)` (CLI-mode)
  - `run_evaluation.py:153` `json.dump(output, f, indent=2)`
- Helper uses `json.dump(data, fh, indent=indent)` with `indent=2` default → same `separators` (`(',', ': ')`), same `ensure_ascii=True`, dict-insertion key order preserved, no trailing newline (matches old).
- Empirically proven byte-identical on a representative payload (nested dicts/lists/floats/bools/None/unicode): old 479 bytes == new 479 bytes, identical tail, both end without trailing newline.
- grep confirms ZERO remaining inline `json.dump`/`json.dumps` in `apps/` — every CV-JSON write now routes through the helper.
- **No format break.** The data/results + paper/tables pipeline reading these files is unaffected.

### (2) run_compare.py read-modify-write crash safety — VERIFIED SAFE
- `compare_model_unified` (`run_compare.py:128-157`): reads `data = json.load(f)` (130-131), mutates the full dict in memory (folds 134-137, intersected_kb 140-143, summary 146), THEN `atomic_json_write(data, cv_file)` (157).
- The full in-memory dict is complete before the helper opens any temp; the source file is NEVER opened in write/truncate mode at the apps layer.
- `atomic_json_write` writes to `tempfile.mkstemp(dir=target.parent)` → `json.dump` → `os.replace(tmp, target)`. The source is only replaced after the temp is fully written and closed.
- Same-filesystem guarantee: temp is created in `target.parent`, so `os.replace` is a true atomic rename on POSIX (no cross-device copy).
- Failure path: on any exception the temp is `os.unlink`'d and the error re-raised; no partial file at target.
- Fault-injection test genuinely proves it: `test_original_untouched_on_replace_failure` (test:102-117) monkeypatches `os.replace` to raise OSError AND asserts `target.read_text() == original_content`. `test_no_temp_file_left_on_replace_failure` (119-133) asserts no orphan `.tmp`. `test_new_file_not_created_on_replace_failure` (135-147) asserts no partial target when target didn't pre-exist.
- **A mid-write crash leaves the original CV-JSON intact.** Data-loss risk closed.

---

## Findings by severity

### Critical
None.

### High
None.

### Medium

**M1. Non-verbose runs are now fully silent — banner + completion summary lost (behavior change).**
File: `apps/run_congen.py:167-185`, and the equivalent banner/footer blocks in `run_quacq.py`, `run_cv.py`, `run_evaluation.py`, `generate_examples.py`.
OLD code printed the banner (`"="*60`, title, Config/Output/Models/Mode/Solver) and the `Completed: N/M models` footer via UNCONDITIONAL `print()` — visible on every run regardless of `-v`. NEW code routes these through `logger.info(...)`, which `configure_logging` suppresses at the default WARNING level. So a no-flag invocation now emits ZERO stdout (errors still show via `logger.error`).
Impact: limited — documented invocation is `python -m apps.<module> <config.toml> -v`, and the red-team note explicitly wanted "silent batch mode" as the default. But the always-on completion summary and run banner are now gone without `-v`. This is a deliberate-looking design choice that nonetheless changes observable behavior beyond "logging + atomic write."
Fix (if always-on summary is desired): emit the completion footer at WARNING level, OR default `configure_logging` to INFO when no flag is given. Recommend confirming with the operator whether silent-default is intended; if yes, leave as-is and document in the app `--help`/README.

### Low

**L1. `generate_bias_files.py` lazy-import refactor is scope creep (behaviorally equivalent).**
File: `apps/generate_bias_files.py:118-122` (`BatchBiasGenerator.__init__` now does `from conacq.bias import ...` and stores `self._BiasConfigLoader/_BiasGenerator/_BiasIO`).
The module-level import resolves fine now without the removed `os.chdir`/`sys.path.insert` workaround (verified: `import apps.generate_bias_files` succeeds). The instance-level lazy import is unnecessary and deviates from the minimal-scope intent, though it produces identical runtime behavior (same classes, same calls). Recommend reverting to a top-level `from conacq.bias import BiasConfigLoader, BiasGenerator, BiasIO` for clarity — non-blocking.

**L2. `--debug` without `-v` shows less app info than `-v` (double-gating interaction).**
Files: `run_congen.py:68,85,109`, similar in `run_quacq.py`, `run_evaluation.py`, `generate_examples.py`.
Process logs are wrapped in `if verbose: logger.info(...)`. `configure_logging(verbose=False, debug=True)` enables DEBUG/INFO at the handler, but the `if verbose:` guards still skip those INFO lines. Net: `--debug` alone surfaces library DEBUG logs but not the app's own INFO progress lines. Minor inconsistency, harmless. The `if verbose:` guards are now redundant with the level filter (could be dropped) but cause no bug.

**L3. Non-CV-JSON writers intentionally left non-atomic (in scope-bounds, noted for completeness).**
- `extract_results.py:763,768` — markdown + LaTeX table output (`open('w')` + `f.write`). Derived, regenerable paper tables, not the FROZEN CV-JSON. Correctly out of A6 scope.
- `generate_bias_config.py:388` — YAML bias config output. Out of scope.
- `save_kb_result` (`run_congen.py:99`, `run_quacq.py:90`), `save_folds` (`generate_cv_folds.py:70`), `BiasIO.save_to_json/cnf` (`generate_bias_files.py:183,190`), `ExampleIO.save_json` (`generate_examples.py:185`) — library-level writers, never inline `json.dump` in apps. The spec scoped A6 to CV-JSON (run_cv/run_compare/run_evaluation); these `*_kb.json`/folds/bias writers are not atomic but are out of the stated scope. Flag for a future stage if KB-JSON files also need atomic guarantees.

---

## Checklist results

- print() in apps/ = **0** (grep verified). traceback.print_exc = **0**. os.chdir = **0**. (all success criteria met)
- One config-loader: `load_pipeline_config` (a pure `tomllib.load` returning the raw dict) now used by `generate_bias_config`, `generate_examples`, `generate_cv_folds` — behaviorally identical to the old inline `load_config`/`tomllib.load` (same return shape, same `FileNotFoundError` on missing file). Config-loader unit tests (test:154-218) assert `general.output_dir`, `verbose`, and parsed model fields match known values.
- `generate_bias_files.py` switched `import toml` → stdlib `tomllib` with `'r'`→`'rb'` (correct binary-mode requirement). Behaviorally equivalent TOML parse.
- atomic_json_write correctness: temp in `target.parent` (same FS), cleanup on failure, no partial file — all proven by tests.
- Logging preserves `-v` UX: `configure_logging` uses `logging.StreamHandler()` (defaults to stderr in stdlib). NOTE: stdlib `StreamHandler()` with no arg writes to **stderr**, not stdout. The harness docstring/spec says "stdout". See unresolved question Q1 — does not break `-v` visibility (terminal shows both streams) but contradicts the stated "stdout handler" requirement and affects `> file` redirection of progress vs errors.
- No weakened assertions; no result-dataclass/format change; no plan-stage labels in code comments (the `run_evaluation.py` reach-in note describes the why, not a phase label — compliant).
- run_evaluation reach-in (`runner.model.constraint_map`, `runner.feature_ids`) correctly only DOCUMENTED (module docstring + recorded for B1), not "fixed" here — matches spec step 5.

## Positive observations
- atomic_json_write is textbook-correct: mkstemp in target dir, fdopen, replace, unlink-on-failure, re-raise. Docstring explicitly warns callers to build the full dict before calling (guides the read-modify-write contract).
- Fault-injection tests actually assert the load-bearing property (original byte-identical after failed replace) rather than just "raises" — exactly the property a green suite wouldn't otherwise prove.
- Config-loader regression test pins `output_dir == 'data/results'` against a real TOML.
- `exc_info=True` replaces ad-hoc `traceback.print_exc()` — cleaner and respects log level.

## Unresolved questions
- Q1: `configure_logging` uses `logging.StreamHandler()` which defaults to **stderr**, but the spec/docstring say "stdout handler so -v output reaches stdout." Confirm intent: if progress must go to stdout (e.g. for `app ... -v > progress.log`), change to `logging.StreamHandler(sys.stdout)`. Current code still shows `-v` output in a terminal (stderr is visible), so this is not a visibility break, but it contradicts the stated requirement and routes progress to stderr.
- Q2 (M1): Is fully-silent non-verbose output the intended default, or should the `Completed: N/M models` summary remain always-on? OLD behavior printed it unconditionally.

**Status:** DONE_WITH_CONCERNS
**Summary:** A6 PASS — byte-identical CV-JSON verified empirically; read-modify-write crash-safety verified by code + fault-injection tests; 437 effective passes (sole failure is the known flake). Two non-blocking concerns: StreamHandler defaults to stderr vs spec's "stdout" (Q1), and non-verbose runs are now silent including the completion summary (M1).
**Concerns/Blockers:** Q1 (stderr vs stdout) and M1 (silent non-verbose) are observable-behavior items worth a one-line confirmation before commit; neither blocks data integrity.
