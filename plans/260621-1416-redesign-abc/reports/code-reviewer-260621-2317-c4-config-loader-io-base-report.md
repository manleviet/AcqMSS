# Code Review — Stage C4: shared JSON IO mixin (config-loader skipped)

Date: 2026-06-21
Branch: feat/redesign-abc
Scope: uncommitted working-tree only — `conacq/_io_base.py` (new), `conacq/bias/bias_io.py` (M), `conacq/examples/io_utils.py` (M), `tests/test_io_base_roundtrip.py` (new).
Spec: plans/260621-1416-redesign-abc/phase-16-c4-config-loader-io-base.md

## Verdict: PASS

Low-risk boilerplate-dedup as advertised. Byte-identical output proven empirically. FileNotFoundError change behavior-equivalent. No public API change. Config-loader skip justified. Full suite 568 passed / 0 warnings. Only nits: 2 now-unused imports.

---

## Verdicts on required questions

### (1) On-disk byte-identical — CONFIRMED (empirically, not just by inspection)
- Mixin `_write_json` does `open(filepath,'w')` + `json.dump(data, f, indent=2)` — character-for-character the same call the old inline code used in both `BiasIO.save_to_json` and `ExampleIO.save_json`. No `separators`, no `ensure_ascii` override, no trailing newline added (default `ensure_ascii=True`, default separators preserved).
- Proven, not assumed: reconstructed the exact serialized dict and wrote it with the OLD inline `json.dump(...indent=2)` vs the NEW mixin path on the REAL fixtures (`REAL-FM-7-bias.json`, `REAL-FM-7_rs_1n.json`). Result: `old==new bytes: True` for both. Trailing bytes `]\n}` (no extra newline).
- Frozen-format contract is safe.

### (4) Config-loader skip — JUSTIFIED (agree)
Inspected both loaders. They share near-zero:
- `BiasConfigLoader.load` (bias/config_loader.py:30): YAML, **text** mode `open(path,'r')` + `yaml.safe_load`, ~60 lines of field validation, returns a validated `BiasConfig` dataclass, raises KeyError/ValueError on bad fields.
- `load_pipeline_config` (eval/config.py:37): TOML, **binary** mode `open(path,'rb')` + `tomllib.load`, 2-line body, returns a raw `dict`, no validation.
Different file mode (text vs binary), different parser, different return type (validated dataclass vs raw dict), different error surface. A forced shared base would be over-engineering (the only common token is `with open(...)`). The spec's guard clause permits the smaller IO-only unification. YAGNI upheld.

---

## Findings by severity

### Critical — none
### High — none
### Medium — none

### Low

**L1. Now-unused imports in `conacq/bias/bias_io.py`.**
- `bias_io.py:8` `from pathlib import Path` — `Path` no longer referenced (the pre-refactor `Path(filepath).exists()` guard moved into the mixin). Grep confirms zero uses outside the import line.
- `bias_io.py:9` `from typing import Dict` — `Dict` no longer referenced (all annotations use bare `dict`). Zero uses outside the import line.
- Impact: dead imports only; no runtime effect. ruff/flake8 would flag F401.
- Fix: delete both lines. (`io_utils.py` keeps `Path` legitimately — still used at lines 26/60/65.)

**L2. Byte-identical *test* asserts self-consistency, not pre-refactor parity (assertion-strength gap, not a defect).**
- `test_io_base_roundtrip.py:105 test_on_disk_bytes_unchanged` (Bias) and `:187` (Example) do save→reload→save and compare `path1.read_bytes() == path2.read_bytes()`. That proves the writer is *idempotent*, NOT that it matches the OLD inline output. A regression that changed indent/separators uniformly would still pass these two tests.
- The true reference check is `test_write_produces_indent2` (:46) — but it compares against `json.dumps(indent=2)` on a trivial synthetic dict and uses `read_text()` (not `read_bytes()`), so it does not exercise the real fixtures.
- Net: the suite as written would NOT have caught a uniform format drift on the real files. I closed that gap out-of-band (see verdict 1 — empirical old-vs-new on real fixtures passed), so C4 itself is safe. Optional hardening: add one assertion comparing mixin output bytes against an inline `json.dump(...indent=2)` reference built from the same dict. Not blocking.

---

## Checklist results (points 2,3,5)

- **(2) FileNotFoundError change — safe.** `ExampleIO.load_json` previously raised `FileNotFoundError` implicitly via `open()`; now explicit in `_read_json` (`_io_base.py:51-52`). Type unchanged (still `FileNotFoundError`). Message differs (`"File not found: ..."` vs OS errno text) but no caller asserts on the message. Callers (`congen_model_builder.py:119`, `run_cv.py:121`, `generate_cv_folds.py:63`, `run_congen.py:76`, `run_quacq.py:68`) do not wrap in try/except. The only `except FileNotFoundError` handlers in apps (`generate_bias_files.py`, `generate_bias_config.py`) catch exactly that type — still satisfied. Behavior-equivalent, not a regression.
- **(3) BiasIO unchanged externally.** `save_to_cnf` / `save_statistics` untouched (still inline file writes, not JSON). Public methods unchanged. On-disk bias JSON byte-identical (verdict 1). CNF/stats writers not in diff. Prior bias-package-refactoring decisions preserved.
- **(5) Quality gates.**
  - Assertions: 16 tests, all collected, 0 skipped, assert real structure (feature ids, constraint clauses, assignments) on REAL fixtures (`BIAS_PATH`, `EXAMPLES_RS_1N_PATH` both exist). No weakened assertions.
  - No plan-stage labels in code/tests (the grep "matches" were feature names `f1/f2/f3`, not finding codes).
  - conacq-scope: diff touches only `conacq/`; `_io_base.py` imports stdlib only (json, pathlib, typing) — no `explanation/` import, boundary clean.
  - Mixin is private: `_io_base.py` underscore-prefixed module, `JsonSerializationMixin` not re-exported from any `conacq/**/__init__.py`.
  - Docstring `json.JSONDecodeError` mention in `bias_io.py:134` is accurate (propagated by `_read_json`) — not dead code.

## Tests
- Full suite: `uv run --no-sync pytest tests/ -q` → **568 passed in 53.85s, 0 warnings**. No parity flake this run.
- Targeted: `test_io_base_roundtrip.py` + `test_evaluation.py` + `test_congen.py` → 64 passed.

## Unresolved questions
None.
