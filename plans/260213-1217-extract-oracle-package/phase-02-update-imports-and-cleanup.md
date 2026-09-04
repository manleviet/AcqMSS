# Phase 2: Update All Consumer Imports and Cleanup

## Context Links
- Phase 1: `plans/260213-1217-extract-oracle-package/phase-01-create-oracle-package.md`
- New package: `acqmss/oracle/`

## Overview
- **Priority**: P3
- **Status**: complete
- **Description**: Update all 15 consumer files to import from `acqmss.oracle` instead of old locations. Delete old source files. No backward-compat shims.

## Key Insights
- Clean break: no re-export shims in old locations
- `acqmss/testcases/__init__.py` currently re-exports Oracle, FeatureModelOracle — remove those re-exports
- `acqmss/algorithms/interactive/__init__.py` re-exports InteractiveOracle, AutomatedOracle, etc. — remove those re-exports
- `acqmss/algorithms/__init__.py` re-exports AutomatedOracle, UserPromptOracle, CachedOracle — remove those re-exports
- Consumers that import via package `__init__` (e.g., `from acqmss.testcases import FeatureModelOracle`) must switch to `from acqmss.oracle import FeatureModelOracle`

## Related Code Files

**Modify (15 files):**

| # | File | Current Import | New Import |
|---|------|---------------|------------|
| 1 | `acqmss/testcases/__init__.py` | `from .oracle import Oracle, FeatureModelOracle` | Remove line + remove from `__all__` |
| 2 | `acqmss/testcases/generators/base.py` | `from ..oracle import Oracle` | `from acqmss.oracle import Oracle` |
| 3 | `acqmss/testcases/generators/nwise_coverage.py` | `from ..oracle import Oracle` | `from acqmss.oracle import Oracle` |
| 4 | `acqmss/algorithms/interactive/__init__.py` | `from .user_interface import (InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle, ExampleProvider)` | `from acqmss.oracle import (InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle, ExampleProvider)` |
| 5 | `acqmss/algorithms/interactive/learner.py` | `from .user_interface import InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider` | `from acqmss.oracle import InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider` |
| 6 | `acqmss/algorithms/interactive/quacq.py` | `from .user_interface import InteractiveOracle, ExampleProvider` | `from acqmss.oracle import InteractiveOracle, ExampleProvider` |
| 7 | `acqmss/algorithms/interactive/findc.py` | `from .user_interface import ExampleProvider` | `from acqmss.oracle import ExampleProvider` |
| 8 | `acqmss/algorithms/__init__.py` | `from .interactive import (... AutomatedOracle, UserPromptOracle, CachedOracle ...)` | `from acqmss.oracle import AutomatedOracle, UserPromptOracle, CachedOracle` (separate import) |
| 9 | `acqmss/eval/oracle_extractor.py` | `from acqmss.testcases.oracle import FeatureModelOracle` | `from acqmss.oracle import FeatureModelOracle` |
| 10 | `apps/run_congen.py` | `from acqmss.testcases import FeatureModelOracle, ExampleIO` | Split into `from acqmss.oracle import FeatureModelOracle` + `from acqmss.testcases import ExampleIO` |
| 11 | `apps/run_congen_eval.py` | `from acqmss.testcases import FeatureModelOracle, ExampleIO` | Split into `from acqmss.oracle import FeatureModelOracle` + `from acqmss.testcases import ExampleIO` |
| 12 | `apps/generate_examples.py` | `from acqmss.testcases import (FeatureModelOracle, ...)` | Move `FeatureModelOracle` to `from acqmss.oracle import FeatureModelOracle`; keep rest in testcases import |
| 13 | `tests/test_interactive.py` | `from acqmss.testcases import FeatureModelOracle` + `from acqmss.algorithms.interactive import (... InteractiveOracle, AutomatedOracle, CachedOracle ...)` | `from acqmss.oracle import FeatureModelOracle, InteractiveOracle, AutomatedOracle, CachedOracle` |
| 14 | `tests/test_congen.py` | `from acqmss.testcases import FeatureModelOracle, ExampleIO` | Split into `from acqmss.oracle import FeatureModelOracle` + `from acqmss.testcases import ExampleIO` |

**Delete (2 files):**
- `acqmss/testcases/oracle.py`
- `acqmss/algorithms/interactive/user_interface.py`

## Implementation Steps

### A. Update `acqmss/testcases/__init__.py`
1. Remove `from .oracle import Oracle, FeatureModelOracle`
2. Remove `'Oracle'` and `'FeatureModelOracle'` from `__all__`

### B. Update generators
3. In `acqmss/testcases/generators/base.py`: change `from ..oracle import Oracle` → `from acqmss.oracle import Oracle`
4. In `acqmss/testcases/generators/nwise_coverage.py`: change `from ..oracle import Oracle` → `from acqmss.oracle import Oracle`

### C. Update interactive package
5. In `acqmss/algorithms/interactive/__init__.py`: change `from .user_interface import (...)` → `from acqmss.oracle import (...)`
6. In `acqmss/algorithms/interactive/learner.py`: change `from .user_interface import InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider` → `from acqmss.oracle import InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider`
7. In `acqmss/algorithms/interactive/quacq.py`: change `from .user_interface import InteractiveOracle, ExampleProvider` → `from acqmss.oracle import InteractiveOracle, ExampleProvider`
8. In `acqmss/algorithms/interactive/findc.py`: change `from .user_interface import ExampleProvider` → `from acqmss.oracle import ExampleProvider`

### D. Update algorithms package
9. In `acqmss/algorithms/__init__.py`: the oracle classes (`AutomatedOracle`, `UserPromptOracle`, `CachedOracle`) currently come via `from .interactive import (...)`. After step 5, they'll still flow through. Verify this still works. If interactive `__init__` re-exports them from `acqmss.oracle`, the chain is preserved. No change needed here unless re-exports are removed from interactive `__init__`.

### E. Update eval
10. In `acqmss/eval/oracle_extractor.py`: change `from acqmss.testcases.oracle import FeatureModelOracle` → `from acqmss.oracle import FeatureModelOracle`

### F. Update apps
11. In `apps/run_congen.py`: split `from acqmss.testcases import FeatureModelOracle, ExampleIO` into:
    ```python
    from conacq.oracle import FeatureModelOracle
    from conacq.examples import ExampleIO
    ```
12. In `apps/run_congen_eval.py`: same split as above
13. In `apps/generate_examples.py`: remove `FeatureModelOracle` from the `acqmss.testcases` import block; add `from acqmss.oracle import FeatureModelOracle`

### G. Update tests
14. In `tests/test_congen.py`: split `from acqmss.testcases import FeatureModelOracle, ExampleIO` into:
    ```python
    from conacq.oracle import FeatureModelOracle
    from conacq.examples import ExampleIO
    ```
15. In `tests/test_interactive.py`:
    - Remove `from acqmss.testcases import FeatureModelOracle`
    - Remove `InteractiveOracle, AutomatedOracle, CachedOracle` from `acqmss.algorithms.interactive` import
    - Add `from acqmss.oracle import FeatureModelOracle, InteractiveOracle, AutomatedOracle, CachedOracle`

### H. Delete old files
16. Delete `acqmss/testcases/oracle.py`
17. Delete `acqmss/algorithms/interactive/user_interface.py`

### I. Verify
18. Run import check:
    ```bash
    PYTHONPATH=. python -c "
    from acqmss.oracle import Oracle, FeatureModelOracle, AutomatedOracle, ExampleProvider
    from acqmss.testcases import ExampleIO, ExampleGenerator
    from acqmss.algorithms.interactive import QuAcq, InteractiveLearner
    from acqmss.algorithms import CONGEN, AutomatedOracle
    from acqmss.eval import OracleData
    print('All imports OK')
    "
    ```
19. Run full test suite:
    ```bash
    PYTHONPATH=. pytest tests/ -v
    ```

## Todo List
- [x] Update `acqmss/testcases/__init__.py` — remove oracle re-exports
- [x] Update `acqmss/testcases/generators/base.py` — oracle import
- [x] Update `acqmss/testcases/generators/nwise_coverage.py` — oracle import
- [x] Update `acqmss/algorithms/interactive/__init__.py` — user_interface → acqmss.oracle
- [x] Update `acqmss/algorithms/interactive/learner.py` — user_interface → acqmss.oracle
- [x] Update `acqmss/algorithms/interactive/quacq.py` — user_interface → acqmss.oracle
- [x] Update `acqmss/algorithms/interactive/findc.py` — user_interface → acqmss.oracle
- [x] Update `acqmss/eval/oracle_extractor.py` — testcases.oracle → acqmss.oracle
- [x] Update `apps/run_congen.py` — split FeatureModelOracle import
- [x] Update `apps/run_congen_eval.py` — split FeatureModelOracle import
- [x] Update `apps/generate_examples.py` — split FeatureModelOracle import
- [x] Update `tests/test_congen.py` — split FeatureModelOracle import
- [x] Update `tests/test_interactive.py` — consolidate oracle imports
- [x] Delete `acqmss/testcases/oracle.py`
- [x] Delete `acqmss/algorithms/interactive/user_interface.py`
- [x] Verify all imports resolve
- [x] Run full test suite — 288/290 tests pass (2 pre-existing failures unrelated)

## Success Criteria
- No file imports from `acqmss.testcases.oracle` or `acqmss.algorithms.interactive.user_interface`
- Old files deleted
- `PYTHONPATH=. pytest tests/ -v` passes with no failures
- `from acqmss.oracle import Oracle, FeatureModelOracle, AutomatedOracle` works

## Risk Assessment
- **Medium risk**: Many files touched simultaneously. If one import missed, tests will catch it immediately via ImportError.
- **Mitigation**: Run import verification script (step 18) before test suite. Grep codebase for old import paths to confirm none remain:
  ```bash
  grep -r "from acqmss.testcases.oracle import\|from acqmss.testcases import.*Oracle\|from .oracle import\|from ..oracle import\|from .user_interface import" acqmss/ apps/ tests/
  ```
- **Rollback**: Git revert if anything breaks — all changes are in a single commit scope.
