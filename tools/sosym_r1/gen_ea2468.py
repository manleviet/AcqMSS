#!/usr/bin/env python3
"""
Driver for the ea2468 example-set + CV-fold generation (SoSyM revision, C5).

Why this exists rather than "just run the app": the committed configs list five
other knowledge bases, and ``generate_examples.py`` has no skip-if-exists — a
plain run overwrites 30 committed example files the paper's numbers depend on.
This driver builds a throwaway config containing **only ea2468 and one
strategy**, and asserts before and after every run that no other knowledge
base's file moved. The protection is structural, not a warning in a prompt.

It also records wall-clock, peak RSS and the resulting counts into
``tools/sosym_r1/measurements.jsonl`` so the cost report is a byproduct of the
run rather than something reconstructed afterwards.

Usage (from the repo root, on the branch feat/sosym-r1):

    python3 tools/sosym_r1/gen_ea2468.py examples ff
    python3 tools/sosym_r1/gen_ea2468.py examples rs_1n
    python3 tools/sosym_r1/gen_ea2468.py examples rs_2n
    python3 tools/sosym_r1/gen_ea2468.py examples rs_3n
    python3 tools/sosym_r1/gen_ea2468.py examples 2cov --no-timeout
    python3 tools/sosym_r1/gen_ea2468.py examples rs_m --m <2-COV count>
    python3 tools/sosym_r1/gen_ea2468.py folds
    python3 tools/sosym_r1/gen_ea2468.py report

``rs_m`` refuses to run without ``--m``. With ``m`` absent the app computes it by
running a **full 2-COV pass** (generate_examples.py:152-157), so the natural
"cheapest first" order pays for 2-COV twice. Run 2cov first, take the count off
the report, pass it here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MODEL = "ea2468"
FM_PATH = "data/fms/ea2468.uvl"
N_FEATURES = 1408
SEED = 82
N_FOLDS = 3
STRATEGIES = ["ff", "rs_1n", "rs_2n", "rs_3n", "2cov", "rs_m"]
DEFAULT_GATE_HOURS = 6.0

REPO = Path(__file__).resolve().parents[2]
EX_DIR = REPO / "data" / "examples"
FOLD_DIR = REPO / "data" / "folds"
LEDGER = REPO / "tools" / "sosym_r1" / "measurements.jsonl"


# --------------------------------------------------------------------------
# the guard
# --------------------------------------------------------------------------

def snapshot(directory: Path) -> dict[str, tuple[int, int]]:
    """(size, mtime_ns) for every file in *directory* not belonging to ea2468."""
    out = {}
    if not directory.exists():
        return out
    for p in sorted(directory.iterdir()):
        if p.is_file() and not p.name.startswith(f"{MODEL}_"):
            st = p.stat()
            out[p.name] = (st.st_size, st.st_mtime_ns)
    return out


def assert_untouched(before: dict, after: dict, directory: Path) -> None:
    changed = sorted(
        n for n in set(before) | set(after)
        if before.get(n) != after.get(n)
    )
    if changed:
        raise SystemExit(
            f"\nABORT: files belonging to other knowledge bases changed in "
            f"{directory}:\n  " + "\n  ".join(changed) +
            "\n\nThe run must be discarded and the files restored with "
            "`git checkout -- data/`."
        )


def snapshot_all(directory: Path) -> dict[str, tuple[int, int]]:
    """(size, mtime_ns) for every file in *directory*, ea2468 included."""
    out = {}
    if not directory.exists():
        return out
    for p in sorted(directory.iterdir()):
        if p.is_file():
            st = p.stat()
            out[p.name] = (st.st_size, st.st_mtime_ns)
    return out


def assert_only(before: dict, after: dict, directory: Path, predicate) -> None:
    """Every file that changed must satisfy *predicate* on its name."""
    changed = sorted(
        n for n in set(before) | set(after)
        if before.get(n) != after.get(n)
    )
    illegal = [n for n in changed if not predicate(n)]
    if illegal:
        raise SystemExit(
            f"\nABORT: files outside the permitted set changed in {directory}:\n  "
            + "\n  ".join(illegal) +
            "\n\nThe run must be discarded and the files restored with "
            "`git checkout -- data/`."
        )
    print(f"  guard: {len(changed)} file(s) changed in {directory.name}, all permitted")


# --------------------------------------------------------------------------
# running the app
# --------------------------------------------------------------------------

def run_app(module: str, config_text: str, gate_seconds: float | None) -> dict:
    """Write *config_text* to a temp file, run *module* against it, and return
    wall-clock, peak child RSS, exit status and captured output."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config.toml"
        cfg.write_text(config_text)

        env = dict(os.environ)
        env["PYTHONPATH"] = "."

        rss_before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        t0 = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(
                [sys.executable, "-m", module, str(cfg), "-v"],
                cwd=REPO, env=env, capture_output=True, text=True,
                timeout=gate_seconds,
            )
            rc, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            rc = None
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        elapsed = time.monotonic() - t0
        rss_after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss

    # ru_maxrss is kilobytes on Linux, bytes on macOS.
    unit = 1 if sys.platform == "darwin" else 1024
    return {
        "elapsed_s": round(elapsed, 2),
        "peak_child_rss_mb": round(max(rss_before, rss_after) * unit / 1e6, 1),
        "returncode": rc,
        "timed_out": timed_out,
        "stdout_tail": out[-4000:],
        "stderr_tail": err[-4000:],
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def describe_examples(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    data = json.loads(path.read_text())
    md = data.get("metadata", {})
    return {
        "exists": True,
        "n_positive": len(data.get("positive", [])),
        "n_negative": len(data.get("negative", [])),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "metadata_seed": md.get("seed"),
        "total_combinations": md.get("total_combinations"),
    }


def record(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_examples(args) -> int:
    strategy = args.strategy
    if strategy not in STRATEGIES:
        raise SystemExit(f"unknown strategy {strategy!r}; expected one of {STRATEGIES}")

    if strategy == "rs_m" and args.m is None:
        raise SystemExit(
            "rs_m needs --m. Without it, generate_examples.py:152-157 computes m by "
            "running a full 2-COV pass, so you would pay for 2-COV twice.\n"
            "Run `examples 2cov --no-timeout` first; m is that set's |E+| + |E-|, "
            "which `report` prints for you."
        )

    m_line = f"m = {args.m}\n" if args.m is not None else ""
    config = (
        "[general]\n"
        f"seed = {SEED}\n"
        f'output_dir = "{EX_DIR.relative_to(REPO)}"\n'
        "verbose = true\n"
        f'strategies = ["{strategy}"]\n'
        "\n"
        "[[models]]\n"
        f'path = "{FM_PATH}"\n'
        f"n = {N_FEATURES}\n"
        f"{m_line}"
    )

    gate = None if args.no_timeout else args.gate_hours * 3600.0
    gate_desc = "no wall-clock gate" if gate is None else f"gate {args.gate_hours} h"
    print(f"== ea2468 / {strategy} — {gate_desc} ==")
    print(config)

    before = snapshot(EX_DIR)
    result = run_app("apps.generate_examples", config, gate)
    after = snapshot(EX_DIR)
    assert_untouched(before, after, EX_DIR)

    out_path = EX_DIR / f"{MODEL}_{strategy}.json"
    entry = {"phase": "examples", "strategy": strategy, "m_passed": args.m,
             **result, "output": describe_examples(out_path)}
    record(entry)

    if result["timed_out"]:
        print(f"\nHIT THE GATE after {result['elapsed_s']:.0f} s "
              f"({result['elapsed_s'] / 3600:.2f} h). No output file was written "
              f"(the app saves only at the end of a strategy).")
        print("Recorded. Do not retry with a relaxed criterion — report and stop.")
        return 2
    if result["returncode"] != 0:
        print(f"\nFAILED rc={result['returncode']}")
        print(result["stderr_tail"])
        return 1

    o = entry["output"]
    print(f"\nOK  {result['elapsed_s']:.1f} s ({result['elapsed_s'] / 3600:.2f} h), "
          f"peak child RSS {result['peak_child_rss_mb']} MB")
    print(f"    |E+| = {o['n_positive']}  |E-| = {o['n_negative']}  "
          f"size = {o['size_bytes']:,} B ({o['size_bytes'] / 1e6:.1f} MB)")
    print(f"    sha256 {o['sha256']}")
    if strategy == "2cov":
        m = o["n_positive"] + o["n_negative"]
        print(f"\n    m (2-COV count) = {m}   -> next: "
              f"`python3 tools/sosym_r1/gen_ea2468.py examples rs_m --m {m}`")
    return 0


def cmd_folds(args) -> int:
    present = [s for s in (args.strategies or STRATEGIES)
               if (EX_DIR / f"{MODEL}_{s}.json").exists()]
    missing = [s for s in (args.strategies or STRATEGIES) if s not in present]
    if missing:
        print(f"note: no example set yet for {missing} — skipping those")
    if not present:
        raise SystemExit("no ea2468 example sets found; generate examples first")

    blocks = "".join(
        f'\n[[models]]\nname = "{MODEL}_{s}"\n'
        f'examples = "{(EX_DIR / f"{MODEL}_{s}.json").relative_to(REPO)}"\n'
        for s in present
    )
    config = (
        "[folds]\n"
        f"seed = {SEED}\n"
        f"n_folds = {N_FOLDS}\n"
        f'output_dir = "{FOLD_DIR.relative_to(REPO)}"\n'
        + blocks
    )
    print(f"== ea2468 folds for {present} ==")
    print(config)

    before = snapshot(FOLD_DIR)
    result = run_app("apps.generate_cv_folds", config, None)
    after = snapshot(FOLD_DIR)
    assert_untouched(before, after, FOLD_DIR)

    record({"phase": "folds", "strategies": present, **result})

    if result["returncode"] != 0:
        print(f"FAILED rc={result['returncode']}")
        print(result["stderr_tail"])
        return 1
    for s in present:
        p = FOLD_DIR / f"{MODEL}_{s}_folds.json"
        print(f"  {p.name}: {p.stat().st_size:,} B  sha256 {sha256(p)}"
              if p.exists() else f"  {p.name}: MISSING")
    print(f"\nOK  {result['elapsed_s']:.1f} s")
    return 0


# --------------------------------------------------------------------------
# C11 — regenerate every FF set after the hash-order fix
# --------------------------------------------------------------------------

ALL_MODELS = [
    ("REAL-FM-7", 14), ("arcade-game", 65), ("fqa", 179),
    ("REAL-FM-4", 291), ("busybox-1.18.0", 854), ("ea2468", 1408),
]


def assert_ff_fix_present() -> None:
    """Refuse to regenerate with the unfixed generator.

    `feature_frequency.py` built its `coverage` dict by iterating a set of
    feature names, so the target `_rng.shuffle` picked depended on Python's
    per-process string hashing and the sets were not re-derivable from their
    seed. Regenerating before that line is fixed would produce another
    irreproducible batch, which is the one outcome worth guarding against.
    """
    src = (REPO / "conacq" / "example_generators" / "feature_frequency.py").read_text()
    lines = src.splitlines()
    window = "\n".join(lines[50:66])
    if "sorted(self.features)" not in window or window.count("sorted(self.features)") < 2:
        raise SystemExit(
            "ABORT: the C11 fix is not in place.\n"
            "conacq/example_generators/feature_frequency.py must build `coverage` from\n"
            "`sorted(self.features)` (around line 59), not from the raw set. Without it\n"
            "the regenerated sets would again not be re-derivable from seed 82.\n"
            "Fix the line, then re-run."
        )
    print("  guard: C11 fix present in feature_frequency.py")


def cmd_regen_ff(args) -> int:
    """Regenerate the FF example sets and folds for every knowledge base."""
    assert_ff_fix_present()

    models = [(m, n) for m, n in ALL_MODELS
              if (REPO / "data" / "fms" / f"{m}.uvl").exists()
              and (args.models is None or m in args.models)]
    print(f"== regenerating FF for {[m for m, _ in models]} ==")

    blocks = "".join(
        f'\n[[models]]\npath = "data/fms/{m}.uvl"\nn = {n}\n' for m, n in models
    )
    config = (
        "[general]\n"
        f"seed = {SEED}\n"
        f'output_dir = "{EX_DIR.relative_to(REPO)}"\n'
        "verbose = true\n"
        'strategies = ["ff"]\n'
        + blocks
    )
    print(config)

    before = snapshot_all(EX_DIR)
    result = run_app("apps.generate_examples", config, None)
    after = snapshot_all(EX_DIR)
    assert_only(before, after, EX_DIR, lambda n: n.endswith("_ff.json"))
    record({"phase": "regen-ff-examples",
            "models": [m for m, _ in models], **result})
    if result["returncode"] != 0:
        print(f"FAILED rc={result['returncode']}")
        print(result["stderr_tail"])
        return 1

    fold_blocks = "".join(
        f'\n[[models]]\nname = "{m}_ff"\n'
        f'examples = "data/examples/{m}_ff.json"\n' for m, _ in models
    )
    fold_config = (
        "[folds]\n"
        f"seed = {SEED}\n"
        f"n_folds = {N_FOLDS}\n"
        f'output_dir = "{FOLD_DIR.relative_to(REPO)}"\n'
        + fold_blocks
    )
    fbefore = snapshot_all(FOLD_DIR)
    fresult = run_app("apps.generate_cv_folds", fold_config, None)
    fafter = snapshot_all(FOLD_DIR)
    assert_only(fbefore, fafter, FOLD_DIR, lambda n: n.endswith("_ff_folds.json"))
    record({"phase": "regen-ff-folds", "models": [m for m, _ in models], **fresult})
    if fresult["returncode"] != 0:
        print(f"FAILED rc={fresult['returncode']}")
        print(fresult["stderr_tail"])
        return 1

    print("\n| model | |E+| | |E-| | size | sha256 |")
    print("|---|---|---|---|---|")
    for m, _ in models:
        p = EX_DIR / f"{m}_ff.json"
        d = json.loads(p.read_text())
        print(f"| {m} | {len(d['positive'])} | {len(d['negative'])} | "
              f"{p.stat().st_size:,} B | {sha256(p)} |")
    print("\nCompare each row against `git show conmin-aaai-data:data/examples/<m>_ff.json`.\n"
          "The counts are expected to move; that is the point. The tag is what ConMin's\n"
          "camera-ready supplement ships, so do not delete it.")
    print("\nNow re-run the suite and re-baseline the goldens that read REAL-FM-7_ff.json\n"
          "(tests/test_t11_e2e_learned_kb.py:42 asserts layer3_golden['congen_ff']).")
    return 0


def cmd_report(args) -> int:
    rows = []
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))

    print("| strategy | wall-clock | peak RSS | |E+| | |E-| | size | status |")
    print("|---|---|---|---|---|---|---|")
    for s in STRATEGIES:
        last = None
        for r in rows:
            if r.get("phase") == "examples" and r.get("strategy") == s:
                last = r
        if last is None:
            print(f"| {s} | — | — | — | — | — | not run |")
            continue
        o = last.get("output", {})
        wall = f"{last['elapsed_s']:.1f} s ({last['elapsed_s'] / 3600:.2f} h)"
        rss = f"{last['peak_child_rss_mb']} MB"
        if last["timed_out"]:
            print(f"| {s} | {wall} | {rss} | — | — | — | **hit the gate** |")
            continue
        status = "completed" if last["returncode"] == 0 else f"failed rc={last['returncode']}"
        size = o.get("size_bytes")
        size_cell = f"{size:,} B ({size / 1e6:.1f} MB)" if size else "—"
        print(f"| {s} | {wall} | {rss} | {o.get('n_positive', '—')} | "
              f"{o.get('n_negative', '—')} | {size_cell} | {status} |")

    print("\nsha256 of every produced file:")
    for s in STRATEGIES:
        p = EX_DIR / f"{MODEL}_{s}.json"
        if p.exists():
            print(f"  {p.relative_to(REPO)}  {p.stat().st_size:,} B  {sha256(p)}")
    for s in STRATEGIES:
        p = FOLD_DIR / f"{MODEL}_{s}_folds.json"
        if p.exists():
            print(f"  {p.relative_to(REPO)}  {p.stat().st_size:,} B  {sha256(p)}")

    p2 = EX_DIR / f"{MODEL}_2cov.json"
    if p2.exists():
        d = json.loads(p2.read_text())
        m = len(d.get("positive", [])) + len(d.get("negative", []))
        print(f"\nm (2-COV count) = {m}")
        print(f"total_combinations in metadata = "
              f"{d.get('metadata', {}).get('total_combinations')}")

    print("\nfiles over 50 MB (do NOT commit these; report path + sha256 instead):")
    big = [p for p in list(EX_DIR.glob(f"{MODEL}_*.json")) if p.stat().st_size > 50e6]
    for p in big:
        print(f"  {p.relative_to(REPO)}  {p.stat().st_size / 1e6:.1f} MB")
    if not big:
        print("  (none)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("examples", help="generate one strategy for ea2468")
    pe.add_argument("strategy", choices=STRATEGIES)
    pe.add_argument("--m", type=int, default=None,
                    help="2-COV count, required for rs_m")
    pe.add_argument("--gate-hours", type=float, default=DEFAULT_GATE_HOURS)
    pe.add_argument("--no-timeout", action="store_true",
                    help="lift the wall-clock gate (approved for 2cov only)")
    pe.set_defaults(func=cmd_examples)

    pf = sub.add_parser("folds", help="generate CV folds for the ea2468 sets that exist")
    pf.add_argument("--strategies", nargs="*", default=None)
    pf.set_defaults(func=cmd_folds)

    pg = sub.add_parser("regen-ff",
                        help="C11: regenerate every FF set + folds after the hash-order fix")
    pg.add_argument("--models", nargs="*", default=None)
    pg.set_defaults(func=cmd_regen_ff)

    pr = sub.add_parser("report", help="print the cost table from the ledger")
    pr.set_defaults(func=cmd_report)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
