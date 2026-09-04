# Brainstorm: QuAcqResult Slim Down

## Problem

`QuAcqResult` has 10 fields + 5 methods — bloated DTO doing runner-layer work. `ConGenResult` has 6 fields + 0 methods. Responsibility leak between algorithm and runner layers.

## Analysis

### Field Duplication (QuAcqResult vs QuAcqRunResult/BaseRunResult)

| Field | QuAcqResult | Runner/Base | Verdict |
|-------|-------------|-------------|---------|
| `kb_constraints` | yes | yes (Base) | **Remove** — runner resolves via `model.resolve_kb()` |
| `n_kb` | yes | yes (Base) | **Remove** — derivable from `len(kb_assumption_ids)` |
| `runtime_ms` | yes | yes (Base) | **Remove** — runner extracts from profiler |
| `consistency_checks` | yes | yes (Base) | **Remove** — runner extracts from profiler |
| `metadata` | yes | no | **Remove** — unused |
| `evaluation` | yes | no | **Remove** — dead code, not used anywhere |
| `kb_assumption_ids` | yes | no | **Keep** — primary algorithm output |
| `n_queries` | yes | yes | **Keep** — algorithm metric |
| `convergence_reason` | yes | yes | **Keep** — algorithm metric |
| `query_history` | yes | yes | **Keep** — algorithm trace |

### Methods

| Method | Verdict |
|--------|---------|
| `to_dict()` | **Remove** — serialization is runner's job |
| `save()` | **Remove** — only used in tests |
| `load()` | **Remove** — only used in tests |
| `__post_init__` | **Remove** — was auto-calc for removed `n_kb` |
| `__repr__` | **Keep** — useful for debugging |

### Verification

- `save()`/`load()` — referenced in tests only, zero production usage
- `evaluation` — self-referential only (own `to_dict()`), not consumed by any runner or eval pipeline
- `QuAcqRunner.run()` already reads only: `kb_assumption_ids`, `n_kb`, `n_queries`, `convergence_reason`, `query_history`

## Agreed Solution

### Target Shape

```python
@dataclass
class QuAcqResult:
    """Result of QuAcq constraint acquisition."""
    kb_assumption_ids: List[int] = field(default_factory=list)
    n_queries: int = 0
    convergence_reason: str = ""
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    def __repr__(self):
        return (f"QuAcqResult(n_kb={len(self.kb_assumption_ids)}, n_queries={self.n_queries}, "
                f"convergence='{self.convergence_reason}')")
```

### Impact Map

| File | Change |
|------|--------|
| `conacq/algorithms/quacq/quacq.py` | Slim `QuAcqResult` to 4 fields + `__repr__`. Simplify `_build_result()` |
| `conacq/runners/quacq_runner.py` | Update `run()` — use `len(result.kb_assumption_ids)` for `n_kb` |
| `tests/test_quacq.py` | Update ~10 construction sites, remove serialization tests |
| `conacq/algorithms/quacq/__init__.py` | No change — still exports `QuAcqResult` |

### Risk Assessment

| Risk | Severity | Status |
|------|----------|--------|
| `save()`/`load()` used in production | None | Verified tests-only |
| `evaluation` needed by eval pipeline | None | Verified dead code |
| Runner breaks | None | Already reads only kept fields |
| Test breakage | Low | Straightforward construction site updates |

## Next Steps

1. Slim `QuAcqResult` → 4 fields + `__repr__`
2. Simplify `QuAcq._build_result()`
3. Update `QuAcqRunner.run()` (`n_kb` derivation)
4. Update tests
5. Run test suite
