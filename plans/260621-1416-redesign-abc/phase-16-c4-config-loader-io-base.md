---
phase: 16
title: C4 config-loader + IO base
status: completed
priority: P2
effort: 1-2d
dependencies:
  - 11
---

# Phase 16: C4 — shared ConfigLoader + serialization/IO base

## Overview
Unify the two config loaders (`bias/config_loader.py` YAML vs `eval/config.py` TOML, no common base) and the two parallel serialization classes (`ExampleIO` JSON vs `BiasIO` CNF+JSON+statistics — same `save_json`/`load_json`/`save_statistics` shape, hand-built dicts). One `ConfigLoader` + one serialization/IO base across `bias/`, `eval/`, `examples/`.

## Cross-plan note (MANDATORY)
`plans/260216-1425-bias-package-refactoring/` (status complete) already refactored `config_loader.py` + `bias_io.py`. READ its reports (`plans/260216-1425-bias-package-refactoring/reports/`, plus `plans/reports/code-review-260216-1601-bias-refactoring.md`) BEFORE changing these files, to avoid undoing intentional decisions.

## Requirements
- Functional: a shared `ConfigLoader` base (format-specific subclasses for YAML/TOML); a shared IO base providing `save_json`/`load_json`/`save_statistics`; `BiasIO`/`ExampleIO` extend it.
- Non-functional: file formats on disk unchanged; conacq-side.

## Architecture
- `ConfigLoader` base + `YamlConfigLoader`/`TomlConfigLoader`.
- `SerializationBase` (json save/load + statistics); `BiasIO` adds CNF, `ExampleIO` adds example specifics.

## Related Code Files (verified)
- Modify: `conacq/bias/config_loader.py`, `conacq/eval/config.py` (→ shared ConfigLoader)
- Modify: `conacq/bias/bias_io.py`, `conacq/examples/io_utils.py` (→ shared IO base)
- Note: `apps/` config loaders (A6) should consume this shared loader where applicable
- Add tests for the IO base if `io_utils.py` is untested (verified: untested today)

## Implementation Steps
1. Read the prior bias-package-refactoring reports.
2. Extract `ConfigLoader` base; re-point YAML + TOML loaders.
3. Extract serialization/IO base; re-point `BiasIO` + `ExampleIO`.
4. Add IO-base tests; verify on-disk formats unchanged (round-trip).
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] One `ConfigLoader` base; YAML/TOML are thin subclasses
- [ ] One serialization/IO base; `BiasIO`/`ExampleIO` extend it (no duplicated save/load/statistics)
- [ ] On-disk formats unchanged (round-trip tests)
- [ ] Prior bias-refactoring decisions preserved (or deviation documented)
- [ ] Full suite green (≥351)

## Risk Assessment
- Undoing the completed bias-package-refactoring work → the mandatory report-read is the guard; document any intentional divergence.
