# Brainstorm: Rename InteractiveResult → QuAcqResult

## Problem

`InteractiveResult` is misleadingly generic — produced exclusively by `QuAcq`, consumed by QuAcq-hardwired components. Should mirror `ConGenResult` in `congen.py` pattern.

## Decision

- **Rename** `InteractiveResult` → `QuAcqResult`
- **Move** from `result.py` → `quacq.py` (co-located with `QuAcq`, like `ConGenResult` in `congen.py`)
- **Delete** `result.py` after move
- **Keep** `InteractiveLearner` name unchanged (high-level API wrapper)

## Impact Analysis

### Files to modify (~10 files)

| File | Change |
|------|--------|
| `conacq/algorithms/interactive/quacq.py` | Add `QuAcqResult` dataclass, update internal refs |
| `conacq/algorithms/interactive/result.py` | **DELETE** |
| `conacq/algorithms/interactive/learner.py` | Update import + type hints |
| `conacq/algorithms/interactive/__init__.py` | Update import source + re-export name |
| `conacq/algorithms/acqmss/__init__.py` | Update re-export |
| `conacq/algorithms/__init__.py` | Update re-export |
| `conacq/runners/interactive_runner.py` | Update import + usage |
| `tests/test_interactive.py` | Update import + all references |

### No-impact areas
- **JSON format**: Unchanged (dict keys, no class name stored)
- **`InteractiveRunResult`**: Separate class in runner, no rename needed
- **`ConGenResult`**: Unrelated, no change

## Risk Assessment

- **Low risk**: Pure rename + move. No logic changes.
- **Serena `rename_symbol`** can handle codebase-wide rename automatically.
- File size: `quacq.py` goes from 486 → ~616 lines. Accepted trade-off for co-location.

## Next Steps

1. Move `InteractiveResult` class + imports into `quacq.py`
2. Rename `InteractiveResult` → `QuAcqResult` across codebase
3. Delete `result.py`
4. Update `__init__.py` re-exports (3 files)
5. Run tests to verify
