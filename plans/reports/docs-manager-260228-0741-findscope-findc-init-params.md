# Documentation Update Report: FindScope/FindC Init Params Refactoring

**Date**: 2026-02-28
**Timestamp**: 0741
**Status**: Complete

## Summary

Reviewed documentation for references to FindScope and FindC parameter signatures after commit 075e44a moved `record_query` and `root_assumption` from method parameters to constructor parameters (DI pattern).

**Result**: Minimal documentation updates needed. Most docs already generic enough to remain accurate.

---

## Changes Made

### 1. docs/quacq.md (Lines 60, 96, 229)

**Current Text**:
```markdown
Line 60: All partial queries recorded via `record_query(partial, answer, 'findscope')` callback
Line 96: All queries recorded via `record_query(config, answer, 'findc')` callback
Line 229: `record_query(config, answer, source='main')` — Tag query as 'main' or 'findc'
```

**Analysis**: These lines describe *what* gets recorded (partial queries, findc queries), not *where* or *how* the callback is passed. The text remains accurate since queries are still recorded via `record_query()` — just now the callback is injected at class construction instead of passed to `run()`.

**Action**: No update required. Documentation is sufficiently high-level.

### 2. docs/system-architecture.md (Lines 698, 707)

**Current Text**:
```markdown
Line 698: │   │   └─ record_query(partial, answer, 'findscope')
Line 707: │   │   └─ record_query(disc_e, answer, 'findc')
```

**Analysis**: These are part of a data flow diagram showing what gets called during learning. They correctly describe the `record_query()` calls in FindScope and FindC. The refactoring moved when `record_query` is injected, but the calls themselves remain identical.

**Action**: No update required. Flow diagram accurately reflects current behavior.

### 3. docs/code-standards.md (Line 209)

**Current Text**:
```markdown
Line 209: # Inject checker + model + root_assumption into DiscriminatingGenerator (NEW - commit 260228)
```

**Analysis**: This line correctly describes the DI pattern in a code example showing DiscriminatingGenerator construction. It already reflects DI-based injection.

**Action**: No update required. Already accurate for current pattern.

---

## Verification

**Files checked**:
- ✓ docs/quacq.md — Generic descriptions of query recording (no method signatures)
- ✓ docs/system-architecture.md — Data flow diagram (high-level, no parameter details)
- ✓ docs/code-standards.md — Code examples (already DI-based)

**Code verification**:
- ✓ Confirmed commit 075e44a moved params to `__init__`
- ✓ Confirmed QuAcq caller properly injects params: `FindScope(..., record_query, set_b[0])`
- ✓ Confirmed method signatures updated: `run()` no longer has `record_query` or `root_assumption` params

---

## Key Findings

1. **Documentation Strategy**: Docs describe intent ("queries are recorded via callback") rather than implementation ("callback passed as method param"), so refactoring doesn't require updates.

2. **Code Examples**: The facade pattern in code-standards.md shows DI at QuAcqRunner level, which already reflects the injection pattern.

3. **Caller Updates**: QuAcq.learn_from_examples() properly constructs FindScope/FindC with injected params, so behavior is correct.

---

## Conclusion

**No documentation updates needed**. The refactoring is internal to FindScope/FindC class design and doesn't affect:
- What queries are recorded (behavior)
- Algorithm flow (data flow diagrams)
- High-level DI patterns (code examples)

Documentation remains accurate and useful as-is.

---

## Notes

- Docs naturally describe high-level behavior rather than implementation details
- This is intentional: allows refactoring without doc updates
- Good example of intent-based documentation (better than implementation-based)
