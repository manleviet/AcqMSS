# Brainstorm: Oracle use_incremental Configuration

## Problem
`BaseRunner.__init__()` hardcodes `use_incremental=False` for Oracle. For fair algorithm comparison, Oracle should use the configured value.

## Analysis
- **No technical constraint** forcing `use_incremental=False` — Oracle's KB is fixed after build, only assumptions change between `is_valid()` calls. Incremental mode is safe and faster.
- `OneShotModel` in interactive flow correctly hardcodes `False` (one-shot, disposable checkers).
- Oracle checker is **reused** across many calls → incremental mode benefits are real.

## Agreed Approach
**Approach A: BaseRunner receives `use_incremental` param, passes to Oracle.**

### Changes Required
1. `BaseRunner.__init__` — add `use_incremental` param → pass to `FeatureModelOracle`
2. `ConGenRunner.__init__` — pass existing `use_incremental` to `super().__init__()`
3. `InteractiveRunner.__init__` — add `use_incremental` param → pass to `super().__init__()`
4. `InteractiveModel` — add `use_incremental` support (user decision, future-proofing)
5. TOML config — add `use_incremental` for interactive config
6. Tests — verify both modes work

## Decisions
- InteractiveModel gets `use_incremental` despite currently using OneShotModel (future-proofing per user request)
- Default: `use_incremental=True` (match existing ConGen default)
- TOML config updated for both algorithms
