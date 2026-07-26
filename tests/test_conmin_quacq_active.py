"""Tests for the QuAcq-active (oracle-mode) ConMin-eval condition additions.

Covers the pure-function pieces added for QuAcq-active (no FM/solver needed):
- uniform `_cost` schema (convergence_reason + provenance columns on every row)
- `aggregate_cv` excludes non-converged QuAcq-active folds from the mean and counts them (H-3)
- `_merge_per_kb` tolerates a purely-additive column delta and warns on provenance conflict
  (H-5 / C-4)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from conacq.eval.conmin_cv_evaluator import (
    _cost, aggregate_cv, _learn_quacq_active, evaluate_kb_example)
from apps.run_conmin_eval import _merge_per_kb

_DATA = Path(__file__).parent.parent / "data"
_FM = _DATA / "fms" / "REAL-FM-7.uvl"
_BIAS = _DATA / "bias" / "REAL-FM-7-bias.json"
_EX = _DATA / "examples" / "REAL-FM-7_ff.json"
_FOLDS = _DATA / "folds" / "REAL-FM-7_ff_folds.json"


# --------------------------------------------------------------------------- #
# _cost uniform schema
# --------------------------------------------------------------------------- #
def test_cost_uniform_schema_across_conditions():
    """Every condition's _cost dict carries the same keys, incl. the additive columns."""
    a_like = _cost(1.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0.0,
                   oracle_queries=0, stage1_batch_checks=None)
    active_like = _cost(2.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0.0,
                        oracle_queries=5000, stage1_batch_checks=None,
                        convergence_reason='max_queries',
                        qa_max_queries=5000, qa_timeout_s=400.0)
    assert set(a_like) == set(active_like)
    for k in ('convergence_reason', 'qa_max_queries', 'qa_timeout_s'):
        assert k in a_like
    # defaults blank/None for non-active; real values for active
    assert a_like['convergence_reason'] == '' and a_like['qa_max_queries'] is None
    assert active_like['convergence_reason'] == 'max_queries'
    assert active_like['qa_max_queries'] == 5000 and active_like['qa_timeout_s'] == 400.0


# --------------------------------------------------------------------------- #
# aggregate_cv H-3: non-converged QuAcq-active excluded from mean, counted
# --------------------------------------------------------------------------- #
def _qa_row(fold, reason, sem_f1):
    return {'kb': 'K', 'example_set': 'ff', 'negatives': 'n/a', 'condition': 'QuAcq-active',
            'k': None, 'fold': fold, 'sem_f1': sem_f1, 'convergence_reason': reason}


def test_aggregate_cv_excludes_nonconverged_quacq_active():
    """3 max_queries folds → n_maxq=3, n_ok_folds=0, NO sem_f1_mean (not averaged as 0)."""
    rows = [_qa_row(0, 'max_queries', 0.0), _qa_row(1, 'max_queries', 0.0),
            _qa_row(2, 'max_queries', 0.0)]
    agg = aggregate_cv(rows)[0]
    assert agg['n_folds'] == 3 and agg['n_ok_folds'] == 0
    assert agg['n_nonconverged'] == 3 and agg['n_maxq'] == 3 and agg['n_timeout'] == 0
    assert 'sem_f1_mean' not in agg  # excluded, never published as a converged number


def test_aggregate_cv_counts_timeout_separately():
    rows = [_qa_row(0, 'timeout', 0.1), _qa_row(1, 'empty_bias', 0.4),
            _qa_row(2, 'empty_bias', 0.6)]
    agg = aggregate_cv(rows)[0]
    # one timeout excluded; two converged folds averaged
    assert agg['n_timeout'] == 1 and agg['n_maxq'] == 0 and agg['n_ok_folds'] == 2
    assert abs(agg['sem_f1_mean'] - 0.5) < 1e-9


def test_aggregate_cv_keeps_passive_quacq_pool_exhausted():
    """Passive QuAcq's pool_exhausted is a normal stop — stays in the mean (not excluded)."""
    rows = [{'kb': 'K', 'example_set': 'ff', 'negatives': 'n/a', 'condition': 'QuAcq',
             'k': None, 'fold': f, 'sem_f1': v, 'convergence_reason': 'pool_exhausted'}
            for f, v in ((0, 0.1), (1, 0.2), (2, 0.3))]
    agg = aggregate_cv(rows)[0]
    assert agg['n_ok_folds'] == 3 and agg['n_nonconverged'] == 0
    assert abs(agg['sem_f1_mean'] - 0.2) < 1e-9


# --------------------------------------------------------------------------- #
# _merge_per_kb H-5 (additive tolerance) / C-4 (provenance conflict)
# --------------------------------------------------------------------------- #
def _write_eval_json(path, rows):
    path.write_text(json.dumps({'rows': rows}))


def test_merge_tolerates_additive_columns(tmp_path, caplog):
    """A pre-column JSON + a with-column JSON merge with NO stale-schema warning."""
    old = [{'kb': 'K', 'example_set': 'ff', 'condition': 'A', 'k': None, 'sem_f1': 0.5}]
    new = [{'kb': 'K', 'example_set': '2cov', 'condition': 'A', 'k': None, 'sem_f1': 0.6,
            'convergence_reason': '', 'qa_max_queries': None, 'qa_timeout_s': None}]
    _write_eval_json(tmp_path / 'K_ff_eval.json', old)
    _write_eval_json(tmp_path / 'K_2cov_eval.json', new)
    with caplog.at_level(logging.WARNING):
        _merge_per_kb(tmp_path)
    assert (tmp_path / 'conmin_eval_long.csv').exists()
    assert 'non-additive' not in caplog.text  # additive delta tolerated, no false warning


def test_merge_warns_on_genuine_stale_schema(tmp_path, caplog):
    """A NON-additive column missing from some rows still warns (real stale-schema mix)."""
    r1 = [{'kb': 'K', 'example_set': 'ff', 'condition': 'A', 'k': None, 'sem_f1': 0.5}]
    r2 = [{'kb': 'K', 'example_set': '2cov', 'condition': 'A', 'k': None}]  # missing sem_f1
    _write_eval_json(tmp_path / 'K_ff_eval.json', r1)
    _write_eval_json(tmp_path / 'K_2cov_eval.json', r2)
    with caplog.at_level(logging.WARNING):
        _merge_per_kb(tmp_path)
    assert 'non-additive' in caplog.text


def test_merge_warns_on_provenance_conflict(tmp_path, caplog):
    """Two QuAcq-active rows for the same (kb,es) with different budgets → provenance warning."""
    rows = [{'kb': 'K', 'example_set': 'ff', 'condition': 'QuAcq-active', 'k': None,
             'sem_f1': 0.0, 'convergence_reason': 'max_queries',
             'qa_max_queries': mq, 'qa_timeout_s': 400} for mq in (5000, 20000)]
    _write_eval_json(tmp_path / 'K_ff_eval.json', rows)
    with caplog.at_level(logging.WARNING):
        _merge_per_kb(tmp_path)
    assert 'provenance conflict' in caplog.text


def test_merge_with_failure_row_preserves_healthy_means(tmp_path, caplog):
    """Regression: a sparse failure row must NOT void healthy groups' means in the CV table.

    (Before the fix, blank-filling the failure flag into every row made aggregate_cv's
    presence-test classify all folds as errored → no means emitted.)"""
    healthy = [{'kb': 'K', 'example_set': 'ff', 'negatives': 'n/a', 'condition': 'A',
                'k': None, 'fold': f, 'sem_f1': v} for f, v in ((0, 0.4), (1, 0.5), (2, 0.6))]
    fail = [{'kb': 'K', 'example_set': '2cov', 'negatives': 'reduced', 'condition': 'C∪S',
             'k': 1, 'fold': 0, 'gate_tripped': 1}]
    _write_eval_json(tmp_path / 'K_ff_eval.json', healthy)
    _write_eval_json(tmp_path / 'K_2cov_eval.json', fail)
    with caplog.at_level(logging.WARNING):
        _merge_per_kb(tmp_path)
    import csv
    cv = {r['condition']: r for r in csv.DictReader(open(tmp_path / 'conmin_eval_cv.csv'))}
    assert cv['A']['n_ok_folds'] == '3' and cv['A']['n_failed'] == '0'
    assert abs(float(cv['A']['sem_f1_mean']) - 0.5) < 1e-9   # healthy mean survives
    assert cv['C∪S']['n_failed'] == '1'                       # failure still counted
    assert 'non-additive' not in caplog.text                  # no false stale-schema warning


def test_aggregate_cv_excludes_max_queries_for_any_condition():
    """H1: passive QuAcq truncated at max_queries is also a partial theory → excluded + counted."""
    rows = [{'kb': 'K', 'example_set': 'ff', 'negatives': 'n/a', 'condition': 'QuAcq',
             'k': None, 'fold': f, 'sem_f1': v, 'convergence_reason': reason}
            for f, v, reason in ((0, 0.0, 'max_queries'), (1, 0.3, 'pool_exhausted'),
                                 (2, 0.5, 'pool_exhausted'))]
    agg = aggregate_cv(rows)[0]
    assert agg['n_maxq'] == 1 and agg['n_ok_folds'] == 2
    assert abs(agg['sem_f1_mean'] - 0.4) < 1e-9  # (0.3+0.5)/2, the max_queries fold dropped


@pytest.mark.slow
def test_evaluate_kb_example_emits_quacq_active_uniform_schema():
    """Integration: a REAL oracle-mode result flows through evaluate_kb_example → a
    'QuAcq-active' row per fold whose key set equals the 'A' row's, with a top-level
    populated convergence_reason + provenance (would have caught a cost-dict/schema bug)."""
    for p in (_FM, _BIAS, _EX, _FOLDS):
        if not p.exists():
            pytest.skip(f"missing test data: {p}")
    res = _learn_quacq_active(str(_BIAS), str(_FM), 'glucose4', True,
                              max_queries=50, timeout_s=600.0)
    rows = evaluate_kb_example(
        'REAL-FM-7', 'ff', str(_FM), str(_BIAS), str(_EX), str(_FOLDS),
        active_res=res, qa_max_queries=50, qa_timeout_s=600.0)
    active = [r for r in rows if r['condition'] == 'QuAcq-active']
    a_rows = [r for r in rows if r['condition'] == 'A']
    assert active and a_rows, "expected both A and QuAcq-active rows"
    # QuAcq-active carries ADDITIVE diagnostic counters (band-aid/findc-unconfirmed/empty-scope/
    # prune-split) for the paper's fairness disclosure; A does not. So the QuAcq-active schema is
    # the A schema PLUS exactly those diagnostic columns.
    DIAG = {'quacq_bandaid_drops', 'quacq_findc_unconfirmed', 'quacq_empty_scope_appends',
            'quacq_prune_partial_pruned', 'quacq_prune_complete_pruned'}
    assert set(active[0]) - DIAG == set(a_rows[0]), \
        "QuAcq-active row schema must match A row schema (plus additive diagnostic counters)"
    assert DIAG <= set(active[0]), "QuAcq-active row must carry all diagnostic counters"
    assert 'convergence_reason' in active[0] and active[0]['convergence_reason']  # top-level
    assert active[0]['qa_max_queries'] == 50 and active[0]['qa_timeout_s'] == 600.0
    assert active[0]['oracle_queries'] == res.n_queries


def test_evaluate_kb_example_disabled_emits_no_quacq_active():
    """Disabled path (active_res=None, no error) emits ZERO QuAcq-active rows."""
    for p in (_FM, _BIAS, _EX, _FOLDS):
        if not p.exists():
            pytest.skip(f"missing test data: {p}")
    rows = evaluate_kb_example('REAL-FM-7', 'ff', str(_FM), str(_BIAS), str(_EX), str(_FOLDS))
    assert not [r for r in rows if r['condition'] == 'QuAcq-active']


def test_evaluate_kb_example_learn_error_emits_per_fold_error_rows():
    """Error path: quacq_active_error → one error-marked QuAcq-active row per fold, and
    aggregate_cv counts them as failed without crashing (group key tolerant of missing negatives)."""
    for p in (_FM, _BIAS, _EX, _FOLDS):
        if not p.exists():
            pytest.skip(f"missing test data: {p}")
    rows = evaluate_kb_example('REAL-FM-7', 'ff', str(_FM), str(_BIAS), str(_EX), str(_FOLDS),
                               quacq_active_error='boom')
    errs = [r for r in rows if r['condition'] == 'QuAcq-active']
    assert errs and all(r.get('error') == 'boom' for r in errs)
    agg = [a for a in aggregate_cv(errs) if a['condition'] == 'QuAcq-active'][0]
    assert agg['n_failed'] == agg['n_folds']
