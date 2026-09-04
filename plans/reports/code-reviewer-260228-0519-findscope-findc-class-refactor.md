# Code Review: FindScope/FindC Class Refactoring

**Date:** 2026-02-28
**Reviewer:** code-reviewer
**Scope:** 4 core files + 2 supporting files (query_provider cleanup)

## Scope

- **Files reviewed:** `findscope.py`, `findc.py`, `quacq.py`, `__init__.py`, `query_provider.py`, `example_generators/__init__.py`
- **Focus:** Correctness, completeness, no broken callers
- **LOC delta:** -11 (317 added, 328 removed)
- **Tests:** 359/359 passed

## Overall Assessment

Clean, correct refactoring. Functions converted to classes with DI-injected collaborators. All call sites updated. No external callers broken (confirmed via grep). Bonus cleanup removed dead code (`generate_with_priority`, priority functions) with zero references.

## Verification Results

| Check | Status |
|-------|--------|
| Recursive `FindScope.run()` uses `self.run()` | PASS |
| `oracle`/`profiler`/`generator` removed from `run()` signatures | PASS |
| Constructor injection wired in `QuAcq.__init__` (lines 76-77) | PASS |
| No external callers of old `find_scope`/`find_c` | PASS (grep confirms only quacq internal usage) |
| Old function names no longer importable from package | PASS |
| New class names exported in `__all__` | PASS |
| All 359 tests pass | PASS |

## Medium Priority

### 1. Unused constructor params: `checker` and `profiler` in both classes

`FindScope.__init__` and `FindC.__init__` accept and store `checker` and `profiler` but neither class uses them in any method.

- `self.checker` -- never referenced after `__init__` in either class
- `self.profiler` -- never referenced after `__init__` in either class

**Impact:** Mild code smell. Extra constructor args create false impression these are dependencies.

**Options:**
- (a) Remove now if not planned for near-term use
- (b) Keep if upcoming work will add `@measure_time` or SAT-based pruning to these classes (YAGNI says remove)

### 2. `FindC.__init__` parameter `checker` not used

Same as above but specifically: `FindC` does Boolean clause evaluation only. If SAT-based checking is planned, `checker` would be needed. Otherwise it's dead weight.

## Low Priority

### 3. `_narrow_with_generator` logic: `is_valid` True removes c_j but not c_i on False

When `is_valid` returns False (disc example is invalid), the algorithm only increments `j` -- it does not remove `c_i`. This matches the paper (Algorithm 3): an invalid discriminating example doesn't tell us which constraint is in the target. Confirmed correct.

### 4. `Optional` import in `findc.py` (line 14) unused

`Optional` is imported but not used in any type annotation. Minor cleanup.

## Positive Observations

1. **DI pattern consistent** -- matches existing `QuAcq`, `DiscriminatingGenerator`, `QueryProvider` constructors
2. **Recursive call correctly refactored** -- `self.run()` replaces `find_scope()` with identical argument lists
3. **`_prune_rejecting_partial` properly moved to instance method** with `self` prefix
4. **Bonus cleanup** -- `generate_with_priority`, `clause_count_priority`, `literal_count_priority` removed with confirmed zero references
5. **`__getattr__` lazy import in example_generators/__init__ simplified** cleanly

## Edge Cases (Scout Findings)

- **No external callers** of `find_scope`/`find_c` exist outside `quacq.py` -- confirmed safe
- **`remaining_bias` mutation** via `set.discard()` in `_narrow_with_generator` -- shared mutable state between `FindC` and `QuAcq.learn()` is the intended design (bias shrinks as constraints are eliminated)
- **Thread safety** -- not a concern; QuAcq is single-threaded per learn() invocation
- **Deep recursion in `FindScope.run()`** -- O(log|X|) depth where X=features; for typical FM sizes (<1000 features) this is safe

## Recommended Actions

1. **[Medium]** Remove unused `checker` and `profiler` from `FindScope.__init__` and `FindC.__init__` unless there's a concrete near-term plan to use them
2. **[Low]** Remove unused `Optional` import from `findc.py` line 14

## Unresolved Questions

- Is there a planned use for `checker`/`profiler` in FindScope/FindC? If so, keeping them is fine as forward-looking DI. If not, YAGNI applies.
