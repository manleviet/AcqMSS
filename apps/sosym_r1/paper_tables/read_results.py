"""The generator's readers: committed JSON in, per-fold aggregates out.

ONE AGGREGATION, STATED ONCE. Every quality metric here is the mean over folds,
per the standing rule that a quoted number must name its aggregation. The two
other aggregations that exist in these files -- the intersected KB, and a pooled
figure -- are deliberately unreachable from this module: each has already produced
a published number that was not the one the paper computes.

The gate (``check_paper_tables.py``) does NOT import this module. It re-reads the
same JSON with its own code, so a mistake here has to be made twice, identically,
to survive.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from .frozen import is_not_run


class Missing(Exception):
    """A file the tables need is absent. Never swallowed into a blank cell."""


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _folds(doc: dict | None) -> list[dict]:
    return (doc or {}).get("folds") or []


def _tier(fold: dict, tier: str) -> dict:
    """``evaluation.<tier>.metrics``.

    The nesting matters: one level shallower holds the strategy label rather than
    numbers, and reading it returns a ``.get`` default of 0 on every fold -- which
    is how "the precision and recall do not exist anywhere" was once reported.
    """
    return ((fold.get("evaluation") or {}).get(tier) or {}).get("metrics") or {}


def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return st.mean(values), (st.stdev(values) if len(values) > 1 else 0.0)


class ResultTree:
    """The one acquisition tree every table is computed from."""

    def __init__(self, root: Path):
        self.root = root
        self.congen = root / "congen"
        self.interactive = root / "interactive"

    # ---------------------------------------------------------------- passive
    def congen_doc(self, stem: str, sampling: str) -> dict | None:
        return _load(self.congen / f"{stem}_{sampling}_cv_incremental.json")

    def congen_folds(self, stem: str, sampling: str) -> list[dict]:
        return _folds(self.congen_doc(stem, sampling))

    # --------------------------------------------------------------- iterative
    def iterative_folds(self, stem: str, sampling: str, mode: str) -> list[dict]:
        return _folds(_load(
            self.interactive / f"{stem}_{sampling}_cv_incremental_{mode}.json"))

    # ------------------------------------------------------------------ values
    def accuracy(self, folds: list[dict]) -> tuple[float | None, float | None]:
        return mean_sd([f["accuracy"] for f in folds if f.get("accuracy") is not None])

    def tier_f1(self, folds: list[dict], tier: str) -> float | None:
        vals = [_tier(f, tier).get("f1_score") for f in folds if _tier(f, tier)]
        vals = [v for v in vals if v is not None]
        return st.mean(vals) if vals else None

    def semantic(self, folds: list[dict], key: str) -> float | None:
        vals = [_tier(f, "semantic").get(key) for f in folds if _tier(f, "semantic")]
        vals = [v for v in vals if v is not None]
        return st.mean(vals) if vals else None

    def exact_equivalence(self, folds: list[dict]) -> tuple[int, int]:
        """(attained, scored). Scored counts folds where the check actually ran."""
        scored = [f for f in folds if (f.get("evaluation") or {}).get("exact_equiv") is not None]
        attained = [f for f in scored
                    if (f.get("evaluation") or {})["exact_equiv"] in (1, True)]
        return len(attained), len(scored)

    def statistic(self, folds: list[dict], key: str) -> float | None:
        vals = [(f.get("statistics") or {}).get(key) for f in folds]
        vals = [v for v in vals if v is not None]
        return st.mean(vals) if vals else None

    def runtime_ms(self, folds: list[dict]) -> float | None:
        vals = [(f.get("performance") or {}).get("runtime_ms") for f in folds]
        vals = [v for v in vals if v is not None]
        return st.mean(vals) if vals else None

    def queries(self, folds: list[dict]) -> float | None:
        vals = [f.get("n_queries") for f in folds if f.get("n_queries") is not None]
        return st.mean(vals) if vals else None

    def stop_reasons(self, folds: list[dict]) -> list[str]:
        return sorted({f["convergence_reason"] for f in folds
                       if f.get("convergence_reason")})

    # ------------------------------------------------------------------ phases
    def phases_ms(self, folds: list[dict]) -> dict[str, float | None]:
        """Per-phase wall clock, in milliseconds, as per-fold means.

        THE SCOPES, measured over all 84 folds rather than assumed:

          ``reduce_runtime_ms`` is INSIDE ``congen_runtime_ms``     (0 violations)
          ``shared_preprocessing_runtime`` is DISJOINT from it      (0 violations)
          their sum is within ``runtime_ms``                        (0 violations)
          ``profiler.congen_total_time`` == ``runtime_ms``          (0 violations)

        So AcqMss is the acquisition loop minus Reduce, and preprocessing is NOT
        subtracted from the loop -- it was never part of it. Subtracting it anyway
        printed a NEGATIVE AcqMss duration for KB2, and the cell gate agreed,
        because a re-derivation that shares the definition agrees with a wrong one.
        The containment above is now asserted by audit_tables/properties.py, which
        does not share this expression.

        The three phases sum to LESS than the total. The remainder is setup and
        teardown outside every timing scope; it stays unattributed rather than being
        folded into a phase that did not spend it.

        ``acqmss_runtime`` is NOT read. It accumulates over thousands of nested
        recursive calls -- 149.9 s against a 15.2 s run -- so it is not a duration.
        """
        def prof_total(fold: dict, key: str) -> float:
            block = ((fold.get("performance") or {}).get("profiler") or {}).get(key)
            return (block or {}).get("total", 0.0) * 1000.0 if block else 0.0

        acq, red, pre, tot = [], [], [], []
        for f in folds:
            perf = f.get("performance") or {}
            loop = perf.get("congen_runtime_ms")
            if loop is None:
                continue
            reduce_ms = perf.get("reduce_runtime_ms") or 0.0
            red.append(reduce_ms)
            pre.append(prof_total(f, "shared_preprocessing_runtime"))
            acq.append(loop - reduce_ms)
            tot.append(perf.get("runtime_ms") or loop)
        m = lambda xs: st.mean(xs) if xs else None  # noqa: E731
        return {"acqmss": m(acq), "reduce": m(red), "preprocessing": m(pre), "total": m(tot)}

    def phase_checks(self, folds: list[dict]) -> dict[str, float | None]:
        """Per-phase consistency checks, as per-fold means, in the paper's unit."""
        def prof(fold: dict, key: str) -> float:
            return ((fold.get("performance") or {}).get("profiler") or {}).get(key, 0) or 0

        acq = [prof(f, "paper_consistency_checks") for f in folds]
        red = [(f.get("performance") or {}).get("redundancy_consistency_checks") or 0
               for f in folds]
        pre = [prof(f, "shared_preprocessing_quickxplain_checks") for f in folds]
        m = lambda xs: st.mean(xs) if xs else None  # noqa: E731
        out = {"acqmss": m(acq), "reduce": m(red), "preprocessing": m(pre)}
        out["total"] = (None if out["acqmss"] is None
                        else out["acqmss"] + out["reduce"] + out["preprocessing"])
        return out

    def consistency_checks(self, folds: list[dict]) -> float | None:
        vals = [(f.get("performance") or {}).get("consistency_checks") for f in folds]
        vals = [v for v in vals if v is not None]
        return st.mean(vals) if vals else None

    # ------------------------------------------------------------------- guard
    def require(self, stem: str, sampling: str) -> list[dict]:
        """Folds for a unit that is supposed to have them, or a loud failure."""
        folds = self.congen_folds(stem, sampling)
        if not folds and not is_not_run(stem, sampling):
            raise Missing(f"no ConGen result for {stem} {sampling}, and it is not "
                          f"declared as not-run in frozen.py")
        return folds


def example_sizes(examples_dir: Path, stem: str, sampling: str) -> tuple[int, int] | None:
    """(|E+|, |E-|) counted from the committed example set.

    COUNTED, not read from the file's own ``statistics`` block -- and then checked
    against it. The block is a summary written at generation time; the lists are
    what every run actually consumed. If the two ever disagree, the summary is
    stale and the table would otherwise print the stale number without a murmur.
    """
    doc = _load(examples_dir / f"{stem}_{sampling}.json")
    if doc is None:
        return None
    pos, neg = len(doc["positive"]), len(doc["negative"])
    stats = doc.get("statistics") or {}
    declared = (stats.get("n_positive"), stats.get("n_negative"))
    if declared != (None, None) and declared != (pos, neg):
        raise Missing(f"{stem} {sampling}: example lists hold {pos}/{neg} but the "
                      f"file's statistics block declares {declared[0]}/{declared[1]}")
    return pos, neg


def bias_stats(bias_dir: Path, stem: str) -> dict[str, int]:
    """#features, |B| and #clauses, parsed from the committed bias statistics."""
    path = bias_dir / f"{stem}-bias-stats.txt"
    if not path.exists():
        raise Missing(f"bias statistics missing for {stem}: {path}")
    want = {"Total features": "features", "Total constraints": "bias",
            "Total clauses": "clauses"}
    out: dict[str, int] = {}
    for line in path.read_text().splitlines():
        for prefix, key in want.items():
            if line.startswith(prefix):
                out[key] = int(line.split(":")[1].strip())
    missing = set(want.values()) - set(out)
    if missing:
        raise Missing(f"{path} does not state {sorted(missing)}")
    return out
