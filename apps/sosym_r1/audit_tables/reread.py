"""A SECOND reader of the committed JSON, sharing no code with the generator.

Deliberately independent, and deliberately dull. This module must not import
anything from ``apps.sosym_r1.paper_tables`` -- the point of the gate is that a
mistake in the generator's aggregation has to be made twice, identically, before
it can reach the paper. Importing the generator's helpers here would turn the
gate into a comparison of a value with itself, which is the shape that has already
let a whole table ship blank through seven rounds of green checks.

The formatting rules are re-implemented for the same reason. They are three lines
each; a shared formatter would mean a rounding bug renders identically on both
sides and the comparison passes.
"""
from __future__ import annotations

import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def folds(path: Path) -> list[dict]:
    doc = load(path)
    return (doc or {}).get("folds") or []


def avg(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sample_sd(xs: list[float]) -> float | None:
    """Sample standard deviation (n-1), matching what the generator prints."""
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    if len(xs) == 1:
        return 0.0
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def metric(fold: dict, tier: str, key: str):
    ev = fold.get("evaluation") or {}
    block = (ev.get(tier) or {}).get("metrics") or {}
    return block.get(key)


def tier_mean(fs: list[dict], tier: str, key: str) -> float | None:
    return avg([metric(f, tier, key) for f in fs
                if ((f.get("evaluation") or {}).get(tier) or {}).get("metrics")])


def accuracy_mean_sd(fs: list[dict]) -> tuple[float | None, float | None]:
    xs = [f.get("accuracy") for f in fs if f.get("accuracy") is not None]
    return avg(xs), sample_sd(xs)


def stat_mean(fs: list[dict], key: str) -> float | None:
    return avg([(f.get("statistics") or {}).get(key) for f in fs])


def perf_mean(fs: list[dict], key: str) -> float | None:
    return avg([(f.get("performance") or {}).get(key) for f in fs])


def profiler_total_ms(fs: list[dict], key: str) -> float | None:
    out = []
    for f in fs:
        block = ((f.get("performance") or {}).get("profiler") or {}).get(key)
        out.append((block or {}).get("total", 0.0) * 1000.0 if block else 0.0)
    return avg(out)


def profiler_scalar(fs: list[dict], key: str) -> float | None:
    return avg([((f.get("performance") or {}).get("profiler") or {}).get(key, 0) or 0
                for f in fs])


def queries_mean(fs: list[dict]) -> float | None:
    return avg([f.get("n_queries") for f in fs if f.get("n_queries") is not None])


def stop_set(fs: list[dict]) -> list[str]:
    return sorted({f["convergence_reason"] for f in fs if f.get("convergence_reason")})


def equivalence(fs: list[dict]) -> tuple[int, int]:
    scored = [f for f in fs if (f.get("evaluation") or {}).get("exact_equiv") is not None]
    hit = [f for f in scored if (f.get("evaluation") or {})["exact_equiv"] in (1, True)]
    return len(hit), len(scored)


# --------------------------------------------------------------- formatting
# Re-implemented on purpose; see the module docstring.

def fmt_quality(v) -> str:
    return "%.3f" % v


def fmt_count(v) -> str:
    n = int(round(v))
    body = format(abs(n), ",").replace(",", "{,}")
    return ("-" + body) if n < 0 else body


def fmt_pm(mean, sd) -> str:
    return "%.3f $\\pm$ %.3f" % (mean, sd)


# --------------------------------------------------------------- static inputs

def bias_numbers(bias_dir: Path, stem: str) -> dict[str, int]:
    text = (bias_dir / f"{stem}-bias-stats.txt").read_text()
    got = {}
    for line in text.splitlines():
        if line.startswith("Total features:"):
            got["features"] = int(line.split(":")[1])
        elif line.startswith("Total constraints:"):
            got["bias"] = int(line.split(":")[1])
        elif line.startswith("Total clauses:"):
            got["clauses"] = int(line.split(":")[1])
    return got


def example_counts(examples_dir: Path, stem: str, sampling: str) -> tuple[int, int]:
    doc = json.loads((examples_dir / f"{stem}_{sampling}.json").read_text())
    return len(doc["positive"]), len(doc["negative"])
