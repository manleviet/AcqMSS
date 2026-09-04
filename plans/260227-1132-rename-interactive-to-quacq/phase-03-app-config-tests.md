# Phase 3: App + Config + Tests + Example Mode

## Context Links
- [Plan overview](plan.md)
- [Phase 2: Runner Rename](phase-02-runner-rename.md) (prerequisite)
- [Brainstorm](../reports/brainstorm-260227-1132-rename-interactive-to-quacq.md) - example mode design

## Overview
- **Priority**: High
- **Status**: pending
- **Effort**: 40m

Rename app script, TOML config, test file. Add example_only/example_first mode dispatch to `run_quacq.py`. Update TOML section `[interactive]` -> `[quacq]`.

## Key Insights
- `InteractiveRunner.run()` already supports all 4 modes -- the runner layer is complete
- Current `run_interactive.py` only calls `runner.run(mode=mode)` without passing examples -- missing example loading
- Pattern for example loading established in `run_congen.py`: `ExampleIO.load_json(model_config.examples)`
- `ModelConfig.examples` field already exists (optional str path)
- `run_cv_config.toml` has `[evaluation.interactive]` section -- this stays unchanged (it's about algorithm selection, not package name)
- `run_cv.py` reads `config.get('interactive', {})` from `[evaluation.interactive]` -- NOT from the `[interactive]` section being renamed

## Requirements

### Functional
- `python -m apps.run_quacq` works for all 4 modes
- example_only/example_first modes load examples from TOML `examples` field
- automated/interactive modes work as before (no examples needed)

### Non-functional
- Old `apps.run_interactive` module removed (git mv, no alias)
- Config file renamed accordingly

## Related Code Files

### Rename (git mv)
| From | To |
|------|-----|
| `apps/run_interactive.py` | `apps/run_quacq.py` |
| `apps/conf/run_interactive_config.toml` | `apps/conf/run_quacq_config.toml` |
| `tests/test_interactive.py` | `tests/test_quacq.py` |

### TOML Changes
- `run_quacq_config.toml`: `[interactive]` -> `[quacq]`; add `examples` field to `[[models]]`
- `run_cv_config.toml`: `[evaluation.interactive]` stays (it's algorithm config, not package name)

### Code Changes in run_quacq.py
- Import `QuAcqRunner` instead of `InteractiveRunner`
- Import `ExampleIO` from `conacq.examples`
- Add mode dispatch logic for example_only/example_first
- Read config from `[quacq]` section instead of `[interactive]`

## Architecture

### Mode Dispatch Logic (run_quacq.py)

```python
quacq_config = config.get('quacq', {})
mode = 'interactive' if args.interactive else quacq_config.get('mode', 'automated')

if mode in ('example_only', 'example_first'):
    if not model_config.examples:
        raise ValueError(f"Mode '{mode}' requires examples path in [[models]]")
    examples = ExampleIO.load_json(model_config.examples)
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    run_result = runner.run(positive_examples=pos, negative_examples=neg, mode=mode)
else:
    run_result = runner.run(mode=mode)
```

Pattern follows `run_congen.py` L73-75: `ExampleIO.load_json()` returns `ExampleSet`, extract assignments via list comprehension.

## Implementation Steps

### Step 1: Rename Files
1. `git mv apps/run_interactive.py apps/run_quacq.py`
2. `git mv apps/conf/run_interactive_config.toml apps/conf/run_quacq_config.toml`
3. `git mv tests/test_interactive.py tests/test_quacq.py`

### Step 2: Update run_quacq.py
4. Change import: `from conacq.runners import QuAcqRunner`
5. Add import: `from conacq.examples import ExampleIO`
6. Update `config.get('interactive', {})` -> `config.get('quacq', {})`
7. Add example loading in `process_model()`:
   - When mode is `example_only` or `example_first`, require `model_config.examples`
   - Load via `ExampleIO.load_json(model_config.examples)`
   - Extract pos/neg assignments
   - Pass to `runner.run(positive_examples=pos, negative_examples=neg, mode=mode)`
8. Update docstring, usage examples, epilog to reference `run_quacq`
9. Update banner: "Interactive (QuAcq)" -> "QuAcq Constraint Acquisition"
10. Update output filename: `{model_name}_interactive_kb.json` -> `{model_name}_quacq_kb.json`

### Step 3: Update run_quacq_config.toml
11. `[interactive]` -> `[quacq]`
12. Update comment: `python -m apps.run_quacq ...`
13. Add `examples` field to `[[models]]` (commented, with example path)
14. Add `mode` options in comment: `automated | interactive | example_only | example_first`

### Step 4: Update test file
15. In `tests/test_quacq.py`, update all 6 `conacq.algorithms.interactive` imports -> `conacq.algorithms.quacq`
16. Update `InteractiveModel` refs -> `QuAcqModel` (fixture name `interactive_model` can stay or rename to `quacq_model`)
17. Update class name `TestInteractiveModel` -> `TestQuAcqModel`

### Step 5: Update cross-references
18. `apps/run_evaluation.py`: update `interactive_runner` variable name -> `quacq_runner` (cosmetic)
19. `conacq/eval/cross_validation.py`: update variable `runner` type comment if any; function `n_fold_cross_validation_interactive` -- name stays (describes mode, not package)
20. `apps/run_cv.py`: `interactive_config` variable -> `quacq_config` (reads from `[evaluation.interactive]` which stays)
   - Actually NO -- `run_cv.py` reads `eval_config.get('interactive', {})` from `[evaluation.interactive]` -- this is about algorithm config, not the renamed package. Leave it as-is to avoid breaking CV config.

### Step 6: Verify
21. Run `PYTHONPATH=. pytest tests/ -v`
22. Test manually: `PYTHONPATH=. python -m apps.run_quacq apps/conf/run_quacq_config.toml -v`

## Todo List

- [ ] git mv apps/run_interactive.py -> apps/run_quacq.py
- [ ] git mv apps/conf/run_interactive_config.toml -> apps/conf/run_quacq_config.toml
- [ ] git mv tests/test_interactive.py -> tests/test_quacq.py
- [ ] Update run_quacq.py (imports, config key, example loading, docstring, banner)
- [ ] Update run_quacq_config.toml ([interactive] -> [quacq], add examples field)
- [ ] Update test file imports and class names
- [ ] Update apps/run_evaluation.py variable names (cosmetic)
- [ ] Run tests -- all pass
- [ ] Manual smoke test: run_quacq in automated mode

## Success Criteria
- `python -m apps.run_quacq apps/conf/run_quacq_config.toml -v` runs successfully
- Example modes load examples from TOML and pass to runner
- All tests pass in `tests/test_quacq.py`
- No references to `run_interactive` or `test_interactive` in `.py` files

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| run_cv.py reads [evaluation.interactive] | CV pipeline breaks | Keep [evaluation.interactive] in run_cv_config.toml unchanged |
| ExampleIO.load_json returns ExampleSet, need assignment lists | Wrong data format | Use `[e.assignments for e in examples.positive]` pattern (same as run_congen.py L74-75) |
| Output filename change breaks downstream tools | Results not found | Document the change; old results with `_interactive_kb.json` remain |

## Next Steps
- Phase 4: Docs Update
