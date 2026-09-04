# C4 Implementation Report: Shared ConfigLoader + IO Base

**Agent:** fullstack-developer  
**Date:** 2026-06-21  
**Phase:** 16 — C4 config-loader + IO base  
**Status:** DONE

---

## 1. Prior Bias-Refactoring Decisions Preserved

Read and audited: `plans/260216-1425-bias-package-refactoring/` (phases 01–03) + `plans/reports/code-review-260216-1601-bias-refactoring.md`.

Decisions preserved — none reversed:

| Decision | Source | Preserved |
|---|---|---|
| All new methods are `_`-prefixed (private), no public API changes | phase-02, phase-03 | Yes — `_write_json`/`_read_json` are `_`-prefixed in the mixin; `_constraint_to_dict`/`_constraint_from_dict` remain unchanged |
| `_MAX_CROSS_TREE_FEATURES_WARNING` is module-level (not class-level) | code-review | Yes — untouched |
| `_constraint_from_dict` trusts `feature_map` completeness (L2, pre-existing behavior) | code-review | Yes — unchanged |
| `save_to_cnf()` not extracted further ("harder to extract without making it less readable") | phase-03 | Yes — untouched |
| `save_statistics()` "no extraction needed" | phase-03 | Yes — untouched |
| `BiasIO.__init__.py` exports unchanged | plan constraints | Yes |
| No logging migration (keep `print()`) | plan constraints | Yes |
| File format on-disk frozen (byte-identical round-trip) | phase-03 risk | Verified by round-trip tests |

---

## 2. Overlap Audit

### Config loaders: `conacq/bias/config_loader.py` (YAML) vs `conacq/eval/config.py` (TOML)

| Dimension | BiasConfigLoader (YAML) | load_pipeline_config (TOML) |
|---|---|---|
| Interface | Full class, `load()` + `validate_config()` + 2 private parsers | Single 3-line function, returns raw `dict` |
| File handle | `open(path, 'r')` (text mode) | `open(path, 'rb')` (binary — required by tomllib) |
| Output type | `BiasConfig` dataclass (structured, validated) | Raw `dict` (callers call `parse_models()` etc. separately) |
| Validation | Extensive (`validate_config()`, required-field checks, value checks) | None (callers handle missing fields) |
| Domain logic | Hierarchical candidates, cross-tree config parsing | `ModelConfig`, `find_cv_files`, `find_kb_files` |
| Shared logic | "open file → parse format → return" | Same shape, different implementation |

**Decision: NO shared base for config loaders.** A `ConfigLoader` base class would be a single-method abstract class where both subclasses override the method body entirely (different file modes, different output types, different validation depth). This is class-hierarchy theater with zero DRY benefit. Forced unification would require either (a) losing type safety on the return type, or (b) a generic `ConfigLoader[T]` that adds complexity for two callsites. KISS/YAGNI: leave as-is, document.

### IO classes: `conacq/bias/bias_io.py` (BiasIO) vs `conacq/examples/io_utils.py` (ExampleIO)

| Method | BiasIO | ExampleIO | Shared pattern |
|---|---|---|---|
| save JSON | `open(fp,'w') + json.dump(data, f, indent=2)` | same | Yes — identical file-write boilerplate |
| load JSON | `Path(fp).exists() check + open + json.load` | `open + json.load` (no existence check) | Partially — same parse, different guard |
| domain-specific | `save_to_cnf()`, `save_statistics()` | `to_dict()`, `from_dict()` | No counterpart |

**Genuine shared logic:** the `open(filepath) + json.dump/load` boilerplate (5 lines each). Extracting to `_write_json` / `_read_json` in a mixin removes this duplication, normalizes the existence-check behavior, and gives a single place to enforce the `indent=2` contract. Real reduction, no forced abstraction.

---

## 3. What Was Implemented

### New file: `conacq/_io_base.py`

`JsonSerializationMixin` with two `@staticmethod` helpers:
- `_write_json(data, filepath)` — `open + json.dump(indent=2)`
- `_read_json(filepath) -> dict` — existence check + `open + json.load`; raises `FileNotFoundError` with context

### Modified: `conacq/bias/bias_io.py`

- `BiasIO` now inherits `JsonSerializationMixin`
- `import json` removed (no longer needed directly)
- `save_to_json`: replaces `open(fp,'w') + json.dump(...)` with `BiasIO._write_json(data, filepath)`
- `load_from_json`: replaces `Path(fp).exists() check + open + json.load` with `BiasIO._read_json(filepath)` (existence check now inside mixin, error message preserved)
- All other methods (`save_to_cnf`, `save_statistics`, `_constraint_to_dict`, `_constraint_from_dict`) unchanged

### Modified: `conacq/examples/io_utils.py`

- `ExampleIO` now inherits `JsonSerializationMixin`
- `import json` removed (no longer needed directly)
- `save_json`: replaces `open(fp,'w') + json.dump(...)` with `ExampleIO._write_json(data, filepath)` (directory creation logic unchanged)
- `load_json`: replaces `open(fp,'r') + json.load` with `ExampleIO._read_json(filepath)` (adds FileNotFoundError guard that was previously missing)
- `to_dict`, `from_dict` unchanged

### New file: `tests/test_io_base_roundtrip.py`

16 tests covering:
- `JsonSerializationMixin._write_json`/`_read_json` unit tests (5)
- `BiasIO` round-trip with real data + byte-identity check + error path + inheritance check (4)
- `ExampleIO` round-trip with synthetic + real data + byte-identity + mkdir + to_dict/from_dict + error path + inheritance check (7)

---

## 4. What Was Deliberately NOT Merged

| Item | Reason |
|---|---|
| `ConfigLoader` base class (YAML + TOML) | Zero genuine shared logic: different file modes, output types, validation depth. A base would be abstract ceremony with no DRY benefit. KISS/YAGNI. |
| `BiasIO.save_to_cnf()` | Format-specific (DIMACS CNF), no counterpart in ExampleIO. Prior refactoring explicitly left this alone. |
| `BiasIO.save_statistics()` | Text statistics format, no counterpart. Prior refactoring explicitly said "no extraction needed." |
| `ExampleIO.to_dict()` / `from_dict()` | In-memory helpers, no counterpart in BiasIO. No shared pattern to extract. |

---

## 5. Test Results

| Suite | Count | Result |
|---|---|---|
| New round-trip tests | 16 | 16 passed |
| Full suite baseline | 552 | — |
| Full suite after changes | 568 | 568 passed, 0 failed, 0 warnings |

On-disk format: verified byte-identical by `test_on_disk_bytes_unchanged` for both BiasIO and ExampleIO using real data files.

---

## 6. Files Modified

| File | Change |
|---|---|
| `conacq/_io_base.py` | NEW — `JsonSerializationMixin` with `_write_json` + `_read_json` |
| `conacq/bias/bias_io.py` | Inherit mixin; use `_write_json`/`_read_json`; remove `import json` |
| `conacq/examples/io_utils.py` | Inherit mixin; use `_write_json`/`_read_json`; remove `import json` |
| `tests/test_io_base_roundtrip.py` | NEW — 16 round-trip + unit tests |

`conacq/bias/config_loader.py` and `conacq/eval/config.py` — **not modified** (no justified shared base).

---

## 7. Deviations from Phase Spec

| Spec item | Decision |
|---|---|
| "One `ConfigLoader` base; YAML/TOML are thin subclasses" | NOT done — see §2 audit. A shared base adds complexity without removing duplication. Documented per spec: "do the SMALLER unification that's genuinely warranted and report what you deliberately did NOT merge + why." |
| "One serialization/IO base; `BiasIO`/`ExampleIO` extend it" | DONE via `JsonSerializationMixin` |
| On-disk formats unchanged | Verified by byte-identical round-trip tests |
| Prior bias-refactoring decisions preserved | Verified — see §1 |

---

## Unresolved Questions

None.

---

**Status: DONE**  
**Summary:** Extracted `JsonSerializationMixin` into `conacq/_io_base.py`; `BiasIO` and `ExampleIO` inherit it and use `_write_json`/`_read_json`. Config-loader unification deliberately skipped (YAML vs TOML share no extractable logic). 568 tests pass (552 baseline + 16 new round-trip tests). On-disk formats frozen and verified byte-identical.
