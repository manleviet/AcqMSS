"""--conditions selector: recompute only QuAcq, surgically merged, A/C/C∪S preserved.

Drives the real run_conmin_eval.main() in-process (full run, then --conditions quacq) and asserts
the A/C/C∪S rows are byte-identical, only QuAcq is recomputed, aggregated is refreshed, --merge
stays well-formed, and a subset run with no existing JSON errors out.
"""
import json
from pathlib import Path

import pytest

import apps.run_conmin_eval as rce
from conacq.eval.conmin_cv_evaluator import aggregate_cv, evaluate_kb_example

_CFG = "apps/conf_conmin/run_conmin_eval_config.toml"
_DATA = Path(__file__).parent.parent / "data"
_HAVE = (Path(_CFG).exists() and (_DATA / "fms" / "REAL-FM-7.uvl").exists()
         and (_DATA / "folds" / "REAL-FM-7_ff_folds.json").exists())


def _run(monkeypatch, out, *extra):
    monkeypatch.setattr("sys.argv", ["run_conmin_eval", _CFG, "--kb", "REAL-FM-7",
                                     "--no-quacq-active", "--example-sets", "ff", "-o", out, *extra])
    rce.main()


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_conditions_quacq_preserves_acs_and_recomputes_quacq(tmp_path, monkeypatch):
    out = str(tmp_path)
    jpath = tmp_path / "REAL-FM-7_ff_eval.json"

    _run(monkeypatch, out)                                   # full run
    full = json.loads(jpath.read_text())
    acs_before = [r for r in full["rows"] if r["condition"] in ("A", "C", "C∪S")]
    assert acs_before and [r for r in full["rows"] if r["condition"] == "QuAcq"]

    _run(monkeypatch, out, "--conditions", "quacq")          # recompute ONLY QuAcq
    after = json.loads(jpath.read_text())
    acs_after = [r for r in after["rows"] if r["condition"] in ("A", "C", "C∪S")]

    assert acs_after == acs_before                           # A/C/C∪S untouched (byte-identical)
    assert [r for r in after["rows"] if r["condition"] == "QuAcq"]      # QuAcq re-emitted
    assert after["aggregated"] == aggregate_cv(after["rows"])            # aggregated refreshed
    assert {r["condition"] for r in after["rows"]} == {"A", "C", "C∪S", "QuAcq"}


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_conditions_subset_without_existing_json_errors(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr("sys.argv", ["run_conmin_eval", _CFG, "--kb", "REAL-FM-7",
                                     "--conditions", "quacq", "-o", str(empty)])
    with pytest.raises(SystemExit):        # must refuse — nothing to reuse
        rce.main()
    assert not list(empty.glob("*_eval.json"))   # no partial JSON written


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_coverage_guard_rejects_narrowed_k(tmp_path, monkeypatch):
    """A subset recompute that would DROP existing (condition,k,neg) rows must refuse + not write."""
    out = str(tmp_path)
    _run(monkeypatch, out)  # full run → C∪S k ∈ {1,2,3,5}
    monkeypatch.setattr("sys.argv", ["run_conmin_eval", _CFG, "--kb", "REAL-FM-7",
                                     "--no-quacq-active", "--example-sets", "ff",
                                     "--conditions", "cus", "--k", "1", "-o", out])
    with pytest.raises(SystemExit):
        rce.main()
    d = json.loads((tmp_path / "REAL-FM-7_ff_eval.json").read_text())
    assert {1, 2, 3, 5} <= {r.get("k") for r in d["rows"] if r["condition"] == "C∪S"}  # untouched


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_quacq_active_selected_but_disabled_rejected(tmp_path, monkeypatch):
    """--conditions quacq-active while QuAcq-active is disabled must NOT delete existing rows."""
    j = tmp_path / "REAL-FM-7_ff_eval.json"
    rows = [{"kb": "REAL-FM-7", "example_set": "ff", "condition": "QuAcq-active", "k": None,
             "negatives": "n/a", "fold": f, "sem_f1": 0.0} for f in range(3)]
    j.write_text(json.dumps({"kb": "REAL-FM-7", "example_set": "ff", "seed": 82,
                             "quacq_active_max_queries": 5000, "quacq_active_timeout_s": 400,
                             "note": "x", "rows": rows, "aggregated": []}))
    monkeypatch.setattr("sys.argv", ["run_conmin_eval", _CFG, "--kb", "REAL-FM-7",
                                     "--example-sets", "ff", "--conditions", "quacq-active",
                                     "--no-quacq-active", "-o", str(tmp_path)])
    with pytest.raises(SystemExit):
        rce.main()
    d = json.loads(j.read_text())  # unchanged
    assert len([r for r in d["rows"] if r["condition"] == "QuAcq-active"]) == 3
    assert d["quacq_active_max_queries"] == 5000


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_invalid_quacq_query_mode_rejected(tmp_path, monkeypatch):
    """A config quacq_query_mode outside the example modes must be rejected (no oracle mislabel)."""
    bad = tmp_path / "bad.toml"
    bad.write_text(Path(_CFG).read_text().replace('quacq_query_mode = "example_only"',
                                                  'quacq_query_mode = "automated"'))
    monkeypatch.setattr("sys.argv", ["run_conmin_eval", str(bad), "--kb", "REAL-FM-7",
                                     "-o", str(tmp_path)])
    with pytest.raises(SystemExit):
        rce.main()


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_empty_conditions_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_conmin_eval", _CFG, "--kb", "REAL-FM-7",
                                     "--conditions", ",", "-o", str(tmp_path)])
    with pytest.raises(SystemExit):
        rce.main()


@pytest.mark.skipif(not _HAVE, reason="REAL-FM-7 fixtures / config missing")
def test_evaluate_kb_example_conditions_filter():
    """Evaluator computes only the requested conditions (no ConMin Stage-1 for QuAcq-only)."""
    args = ("REAL-FM-7", "ff", str(_DATA / "fms" / "REAL-FM-7.uvl"),
            str(_DATA / "bias" / "REAL-FM-7-bias.json"),
            str(_DATA / "examples" / "REAL-FM-7_ff.json"),
            str(_DATA / "folds" / "REAL-FM-7_ff_folds.json"))
    quacq_only = evaluate_kb_example(*args, conditions={"QuAcq"})
    assert quacq_only and {r["condition"] for r in quacq_only} == {"QuAcq"}
    full = evaluate_kb_example(*args)  # conditions=None → A/C/C∪S/QuAcq (no active_res)
    assert {"A", "C", "C∪S", "QuAcq"} <= {r["condition"] for r in full}
