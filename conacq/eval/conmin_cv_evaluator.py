"""ConMin comparison-condition CV evaluator (P4d).

For ONE (KB × example-set): reuse the recorded folds (data/folds/ — the same splits
ConGen/QuAcq use), and per fold score the five comparison conditions on the SAME split:

  A            = maximally specific (mss_ids, k-invariant)
  C            = minimum cover      (cover_ids, k-invariant)
  C∪S          = ConMin             (kb_assumption_ids, sweeps k)
  QuAcq        = passive reference  (example-only QuAcqRunner over the fold examples, k-inv.)
  QuAcq-active = active reference   (oracle-mode QuAcqRunner, self-generated queries vs the FM
                 oracle; learned ONCE per KB, scored on each fold's test set, k-invariant)

Efficiency (§9b): one ConMin ``acquire_pool_and_cover`` per (fold, raw/reduced); the
k-sweep re-runs only ``finish_kb`` (lines 6-8). Cost is attributed per phase from
profiler DELTAS (Stage-1 once, cover once, Reduce per k). Emits long/tidy rows
(one per KB×ex×condition×k×negatives) for the consolidated CSV.
"""
from __future__ import annotations

import logging
import statistics
from pathlib import Path
from typing import Dict, List, Optional

from conacq.oracle import FMOracle
from conacq.oracle.ground_truth import GroundTruthData
from conacq.bias import BiasIO
from conacq.examples import ExampleIO
from conacq.algorithms.conmin import ConMin, ConMinModelBuilder, ConMinTaskInput
from explanation.api import build_checker, SolverBackend
from profiling import profiler_session, ProfilerPreset

from .folds import load_folds, apply_folds
from .kb_comparator import KBComparator
from .conmin_slice_scorer import score_named_kb

K_VALUES = (1, 2, 3, 5)
NEG_MODES = ('reduced', 'raw')


def _timer_ms(prof, key: str) -> float:
    return sum(prof.get_metric(key, [0.0])) * 1000.0


def _counter(prof, key: str) -> int:
    return prof.get_metric(key, 0)


def evaluate_kb_example(
        kb: str, example_set: str, fm_path: str, bias_path: str, examples_path: str,
        folds_path: str, *, k_values=K_VALUES, negatives=NEG_MODES,
        solver_name: str = 'glucose4', use_incremental: bool = True,
        active_res=None, quacq_active_error: Optional[str] = None,
        qa_max_queries=None, qa_timeout_s=None) -> List[dict]:
    """Evaluate all 5 conditions for one (KB, example-set). Returns per-fold rows.

    QuAcq-active (H-6): the oracle-mode theory is learned ONCE per KB by the caller (apps layer)
    and passed in as ``active_res`` (a QuAcqRunResult), reused across every example-set/fold of
    that KB. ``quacq_active_error`` (set instead when the per-KB learn raised) emits a per-fold
    error row. Both None ⇒ QuAcq-active disabled (run_quacq_active=False)."""
    oracle = FMOracle(fm_path, solver_name=solver_name, use_incremental=use_incremental)
    model = (ConMinModelBuilder.from_bias(bias_path)
             .with_oracle_data(oracle.oracle_data).build())
    ground_truth = GroundTruthData.from_uvl(Path(fm_path))
    comparator = KBComparator(ground_truth, BiasIO.load_from_json(bias_path))
    variables = model.name_to_id
    root_clauses = oracle.oracle_data.get_root_clauses()

    examples = ExampleIO.load_json(examples_path)
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    fold_data = load_folds(folds_path)

    rows: List[dict] = []
    try:
        for fold_idx in range(fold_data.n_folds):
            tr_pos, tr_neg, te_pos, te_neg = apply_folds(fold_data, pos, neg, fold_idx)
            meta = dict(kb=kb, example_set=example_set, fold=fold_idx,
                        zero_neg_train=int(len(tr_neg) == 0),
                        n_train_pos=len(tr_pos), n_train_neg=len(tr_neg),
                        n_test_pos=len(te_pos), n_test_neg=len(te_neg),
                        n_test_total=len(te_pos) + len(te_neg))
            for i, neg_mode in enumerate(negatives):
                rows.extend(_eval_conmin_fold(
                    model, oracle, comparator, ground_truth, variables, root_clauses,
                    tr_pos, tr_neg, te_pos, te_neg, k_values, neg_mode, meta,
                    solver_name, use_incremental, emit_a=(i == 0)))
            rows.extend(_eval_quacq_fold(
                bias_path, fm_path, comparator, ground_truth, variables, root_clauses,
                tr_pos, tr_neg, te_pos, te_neg, meta, solver_name, use_incremental))
            # QuAcq-active (H-6): score the per-KB oracle-mode theory on THIS fold's test set.
            if quacq_active_error is not None:
                rows.append({**meta, 'negatives': 'n/a', 'condition': 'QuAcq-active',
                             'k': None, 'error': quacq_active_error})
            elif active_res is not None:
                rows.append(_score_quacq_active_row(
                    active_res, meta, comparator, ground_truth, variables,
                    te_pos, te_neg, root_clauses, qa_max_queries, qa_timeout_s))
    finally:
        oracle.cleanup()
    return rows


def _score_row(meta, negatives, condition, k, names, clauses, fallback_clauses,
               comparator, ground_truth, variables, te_pos, te_neg, root_clauses,
               n_bias, sizes, cost) -> dict:
    """Build one long/tidy row = meta + scorer columns + sizes + per-phase cost."""
    scored = score_named_kb(
        names, clauses, comparator=comparator, ground_truth=ground_truth,
        variables=variables, test_pos=te_pos, test_neg=te_neg,
        bg_clauses=root_clauses, n_bias=n_bias, fallback_clauses=fallback_clauses)
    return {**meta, 'negatives': negatives, 'condition': condition, 'k': k,
            'n_bias': n_bias, **scored, **sizes, **cost}


def _failure_rows(meta, neg_mode, k_values, emit_a, flag, reason) -> List[dict]:
    """B2/B3: on gate-trip or a fold error, emit a marker for EVERY affected
    condition/k so ``aggregate_cv`` counts the failure against each group (not one
    synthetic row). A is only marked when this call owns it (emit_a)."""
    rows = []
    if emit_a:
        rows.append({**meta, 'negatives': 'n/a', 'condition': 'A', 'k': None, flag: reason})
    rows.append({**meta, 'negatives': neg_mode, 'condition': 'C', 'k': None, flag: reason})
    for k in k_values:
        rows.append({**meta, 'negatives': neg_mode, 'condition': 'C∪S', 'k': k, flag: reason})
    return rows


def _eval_conmin_fold(model, oracle, comparator, ground_truth, variables, root_clauses,
                      tr_pos, tr_neg, te_pos, te_neg, k_values, neg_mode, meta,
                      solver_name, use_incremental, emit_a=True) -> List[dict]:
    minimize = (neg_mode == 'reduced')
    rows: List[dict] = []
    try:
        with profiler_session(ProfilerPreset.BENCHMARK) as prof:
            prepared = model.prepare_task(
                ConMinTaskInput.from_examples(oracle.oracle_data, tr_pos, tr_neg),
                minimize=minimize, profiler=prof)
            task, describe = prepared.task, prepared.describe
            # GAP B: GenerateNE preprocessing QuickXplain (k-invariant; reduced only —
            # raw skips QuickXplain via minimize=False). Captured right after prep.
            prep_qx = _counter(prof, 'shared_preprocessing_quickxplain_checks')
            prep_ms = _timer_ms(prof, 'shared_preprocessing_runtime')
            checker = build_checker(
                task, SolverBackend.from_flags(use_incremental=use_incremental),
                solver_name, prof)
            try:
                cm = ConMin(checker, prof)
                state = cm.acquire_pool_and_cover(
                    task.set_c, task.set_b, task.set_tc, task.set_neg_tv,
                    task.negation_map, task.neg_encodings)
                if state is None:  # consistency gate tripped (B3)
                    return _failure_rows(meta, neg_mode, k_values, emit_a,
                                         'gate_tripped', 1)

                # Per-phase cost after lines 1-5 (Stage-1 + cover; both k-invariant).
                stage1_ms = _timer_ms(prof, 'acqmss_runtime')
                cover_ms = _timer_ms(prof, 'conmin_acqmincover_runtime')
                mem = prof.get_metric('memory_peak_mb', 0.0)
                gate = _counter(prof, 'conmin_admpool_gate_checks')
                admp = _counter(prof, 'shared_admpool_checks')
                crej = _counter(prof, 'conmin_cover_rejection_checks')
                cqx = _counter(prof, 'conmin_cover_quickxplain_checks')
                # stage1_batch = paper_consistency_checks (gate + AdmPoolMSS). Cover/Reduce
                # use their own classified counters and do NOT touch it, so it is
                # k-invariant and shared by all three ConMin slices (the ConGen
                # tab:AcqMssruntime-comparable Stage-1 batch number).
                stage1_batch = _counter(prof, 'paper_consistency_checks')
                n_bias = state.n_bias

                # C∪S per k FIRST — clean Reduce deltas (prev_* baselines start at 0
                # with NO prior finish_kb polluting reduce_runtime). The first k's ¬e⁻
                # fallbacks are reused for C (U is k-invariant), so no extra Reduce.
                prev_reduce, prev_redund = 0.0, 0
                u_fallbacks: tuple = ()
                cs_rows: List[dict] = []
                for k in k_values:
                    rk = cm.finish_kb(state, task.support_count, k, task.set_b,
                                      task.negation_map)
                    reduce_ms = _timer_ms(prof, 'reduce_runtime') - prev_reduce
                    prev_reduce += reduce_ms
                    redund = _counter(prof, 'redundancy_consistency_checks') - prev_redund
                    prev_redund += redund
                    _, cs_cl, cs_nm, fb_cl, _ = model.resolve_result(
                        rk, describe, root_clauses, task.set_kb, task.negation_map)
                    if not cs_rows:
                        u_fallbacks = fb_cl
                    cs_rows.append(_score_row(
                        meta, neg_mode, 'C∪S', k, cs_nm, cs_cl, fb_cl, comparator,
                        ground_truth, variables, te_pos, te_neg, root_clauses, n_bias,
                        _sizes(rk.n_mss, len(rk.cover_ids), len(rk.support_ids), rk.n_kb,
                               len(rk.uncoverable), rk.n_components,
                               rk.largest_component, rk.n_greedy_fallback),
                        _cost(stage1_ms, cover_ms, reduce_ms, gate, admp, crej, cqx,
                              redund, mem, oracle_queries=0, stage1_batch_checks=stage1_batch,
                              prep_qx_checks=prep_qx, prep_ms=prep_ms)))

                # A = maximally specific (mss). NE-inert (pool unchanged by raw/reduced)
                # → scored ONCE, labelled negatives='n/a'. Cost = Stage-1. fallback = ().
                if emit_a:
                    a_cl, a_nm = model.resolve_slice(describe, state.mss)
                    rows.append(_score_row(
                        meta, 'n/a', 'A', None, a_nm, a_cl, (), comparator,
                        ground_truth, variables, te_pos, te_neg, root_clauses, n_bias,
                        _sizes(len(state.mss), 0, 0, len(state.mss), 0, 0, 0, 0),
                        # A is NE-inert → 0 preprocessing (it never consumes the reduced
                        # negatives the prep QuickXplain produces). Stage-1 only.
                        _cost(stage1_ms, 0.0, 0.0, gate, admp, 0, 0, 0, mem,
                              oracle_queries=0, stage1_batch_checks=stage1_batch,
                              prep_qx_checks=0, prep_ms=0.0)))

                # C = minimum cover (per neg mode). Cost = Stage-1 + cover; fallback =
                # ¬e⁻ of U (the first k's, U being k-invariant).
                c_cl, c_nm = model.resolve_slice(describe, state.cover_ids)
                rows.append(_score_row(
                    meta, neg_mode, 'C', None, c_nm, c_cl, u_fallbacks, comparator,
                    ground_truth, variables, te_pos, te_neg, root_clauses, n_bias,
                    _sizes(len(state.mss), len(state.cover_ids), 0, len(state.cover_ids),
                           len(state.cover.uncoverable), state.cover.n_components,
                           state.cover.largest_component, state.cover.n_greedy_fallback),
                    _cost(stage1_ms, cover_ms, 0.0, gate, admp, crej, cqx, 0, mem,
                          oracle_queries=0, stage1_batch_checks=stage1_batch,
                          prep_qx_checks=prep_qx, prep_ms=prep_ms)))
                rows.extend(cs_rows)
            finally:
                checker.cleanup()
    except Exception as exc:  # B2: one fold's failure must not void the model
        logging.exception('ConMin fold failed (%s / %s / %s)',
                          meta['kb'], meta['example_set'], neg_mode)
        return _failure_rows(meta, neg_mode, k_values, emit_a, 'error', str(exc))
    return rows


def _eval_quacq_fold(bias_path, fm_path, comparator, ground_truth, variables,
                     root_clauses, tr_pos, tr_neg, te_pos, te_neg, meta,
                     solver_name, use_incremental) -> List[dict]:
    """QuAcq active reference (k-invariant), scored with the SAME scorer/vocab."""
    from conacq.runners import QuAcqRunner
    try:
        runner = QuAcqRunner(bias_path, fm_path, solver_name,
                             use_incremental=use_incremental)
        try:
            # H-2: seed the pool shuffle by fold so example-only QuAcq is reproducible
            # (default shuffle_seed=None draws from OS entropy → nondeterministic oracle_queries).
            res = runner.run(tr_pos, tr_neg, shuffle_seed=meta['fold'])
        finally:
            runner.cleanup()
    except Exception as exc:
        logging.exception('QuAcq fold failed (%s / %s)', meta['kb'], meta['example_set'])
        return [{**meta, 'negatives': 'n/a', 'condition': 'QuAcq', 'k': None,
                 'error': str(exc)}]

    runtime_ms = res.metrics.values.get('runtime_ms', res.runtime_ms) if res.metrics else res.runtime_ms
    # QuAcq's cost is oracle_queries (its paper_consistency_checks counts oracle
    # membership queries, NOT SAT consistency checks) → stage1_batch_checks stays blank
    # so it is never compared against ConMin's Stage-1 batch column.
    return [_score_row(
        meta, 'n/a', 'QuAcq', None, res.kb_constraints, res.kb_clauses, (),
        comparator, ground_truth, variables, te_pos, te_neg, root_clauses, res.n_bias,
        _sizes(0, 0, 0, res.n_kb, 0, 0, 0, 0),
        _cost(runtime_ms, 0.0, 0.0, 0, 0, 0, 0, 0, res.memory_peak_mb,
              oracle_queries=getattr(res, 'n_queries', 0) or 0, stage1_batch_checks=None,
              # Record the real example-only stop (usually 'pool_exhausted') — the direct
              # evidence for WHY passive QuAcq is near-empty. Provenance stays None (passive).
              convergence_reason=getattr(res, 'convergence_reason', '') or ''))]


def _learn_quacq_active(bias_path, fm_path, solver_name, use_incremental,
                        max_queries, timeout_s):
    """Learn QuAcq in oracle/automated mode: self-generated membership queries answered by the
    FM oracle (QueryProvider + DiscriminatingGenerator). Fold- and example-independent (theory =
    f(bias, FM)), so callers learn ONCE per KB and score the single result on each fold's test
    set. ``cleanup()`` in ``finally`` releases the runner's own FMOracle/solver even on
    raise/timeout. Returns the QuAcqRunResult; the caller (apps layer) catches exceptions."""
    from conacq.runners import QuAcqRunner
    runner = QuAcqRunner(bias_path, fm_path, solver_name, query_mode='automated',
                         max_queries=max_queries, timeout_s=timeout_s,
                         use_incremental=use_incremental)
    try:
        return runner.run(mode='automated')
    finally:
        runner.cleanup()


def _score_quacq_active_row(res, meta, comparator, ground_truth, variables,
                            te_pos, te_neg, root_clauses, max_queries, timeout_s) -> dict:
    """Score the oracle-mode QuAcq theory on THIS fold's test set (same scorer/vocab as every
    condition). oracle_queries = active budget spent; stage1_batch_checks blank; convergence_reason
    + provenance (qa_max_queries/qa_timeout_s) recorded. NB structural metrics (sem/desc/clause
    P/R/F1, exact_equiv) are fold-independent — aggregate_cv counts non-converged folds and the
    report presents structural metrics as a single value (H-1/H-3), not a mean±0.000 CV."""
    runtime_ms = (res.metrics.values.get('runtime_ms', res.runtime_ms)
                  if res.metrics else res.runtime_ms)
    return _score_row(
        meta, 'n/a', 'QuAcq-active', None, res.kb_constraints, res.kb_clauses, (),
        comparator, ground_truth, variables, te_pos, te_neg, root_clauses, res.n_bias,
        _sizes(0, 0, 0, res.n_kb, 0, 0, 0, 0),
        _cost(runtime_ms, 0.0, 0.0, 0, 0, 0, 0, 0, res.memory_peak_mb,
              oracle_queries=getattr(res, 'n_queries', 0) or 0, stage1_batch_checks=None,
              convergence_reason=getattr(res, 'convergence_reason', '') or '',
              qa_max_queries=max_queries, qa_timeout_s=timeout_s))


def _sizes(n_mss, n_cover, n_support, n_kb, n_uncoverable, n_components,
           largest_component, n_greedy_fallback) -> dict:
    return {'n_mss': n_mss, 'n_cover': n_cover, 'n_support': n_support, 'n_kb': n_kb,
            'n_uncoverable': n_uncoverable, 'n_components': n_components,
            'largest_component': largest_component, 'n_greedy_fallback': n_greedy_fallback}


def _cost(stage1_ms, cover_ms, reduce_ms, gate, admpool, cover_rej, cover_qx,
          redundancy, memory_mb, oracle_queries=0, stage1_batch_checks=None,
          prep_qx_checks=0, prep_ms=0.0, convergence_reason='',
          qa_max_queries=None, qa_timeout_s=None) -> dict:
    total_ms = stage1_ms + cover_ms + reduce_ms
    # §9c R1-Q4-complete acquisition total (Stage-1 + cover + Reduce), classified sum.
    checks_total = gate + admpool + cover_rej + cover_qx + redundancy
    return {'stage1_ms': stage1_ms, 'cover_ms': cover_ms, 'reduce_ms': reduce_ms,
            'total_ms': total_ms,
            # §4 UNLUMPED, explicit-name columns (no ambiguous "#checks", no atomic —
            # the papers define "checking all E⁺ = ONE consistency check", ConMin l.535
            # = ConGen SoSyM l.549, and the 2γ·log₂(n/γ)+2γ bound is batch):
            'oracle_queries': oracle_queries,        # ConMin 0 · QuAcq N (the scarce cost)
            'stage1_batch_checks': stage1_batch_checks,  # Stage-1 AdmPoolMSS BATCH SAT
                                                  # checks (paper_consistency_checks;
                                                  # ConGen tab:AcqMssruntime-comparable,
                                                  # k-invariant). NOT the per-condition
                                                  # total — cover + Reduce SAT checks are
                                                  # in checks_total. Never an oracle query.
            'checks_total': checks_total,         # §9c classified sum, R1-Q4 (Stage-1 +
                                                  # cover + Reduce) — the TOTAL-table column
            'checks_gate': gate, 'checks_admpool': admpool,
            'checks_cover_rej': cover_rej, 'checks_cover_qx': cover_qx,
            'checks_redundancy': redundancy,
            # GAP B — GenerateNE preprocessing QuickXplain (outside acquire; reduced pays
            # it, raw skips it). Separate from the acquisition totals.
            'preprocessing_checks': prep_qx_checks, 'preprocessing_ms': prep_ms,
            'memory_mb': memory_mb,
            # convergence_reason: QuAcq-active stop reason (empty_bias/no_query/max_queries/
            # timeout); '' for A/C/C∪S; example-only QuAcq now records its real reason too.
            # qa_*: QuAcq-active provenance (None elsewhere) so a budget/timeout-capped row is
            # traceable and --merge can refuse to blend rows with mismatched provenance.
            'convergence_reason': convergence_reason,
            'qa_max_queries': qa_max_queries, 'qa_timeout_s': qa_timeout_s}


# Aggregation column set: numeric metric columns that get CV mean±std.
_AGG_COLS = (
    'size', 'desc_p', 'desc_r', 'desc_f1', 'clause_p', 'clause_r', 'clause_f1',
    'sem_p', 'sem_r', 'sem_f1', 'exact_equiv', 'accuracy', 'specificity',
    'tp', 'tn', 'fp', 'fn', 'n_test_neg',
    'n_mss', 'n_cover', 'n_support', 'n_kb', 'n_uncoverable', 'n_components',
    'largest_component', 'n_greedy_fallback', 'stage1_ms', 'cover_ms', 'reduce_ms',
    'total_ms', 'preprocessing_ms', 'preprocessing_checks', 'oracle_queries',
    'stage1_batch_checks', 'checks_total', 'checks_gate', 'checks_admpool',
    'checks_cover_rej', 'checks_cover_qx', 'checks_redundancy', 'memory_mb',
)


def aggregate_cv(rows: List[dict]) -> List[dict]:
    """CV mean±std per (kb, example_set, negatives, condition, k) across folds.

    Rows carrying an ``error``/``gate_tripped`` flag are excluded from the mean but
    counted (n_failed / n_zero_neg_folds) so a degenerate fold never silently skews it
    (B3). Any row whose ``convergence_reason`` is ``timeout``/``max_queries`` (a QuAcq or
    QuAcq-active learn capped by budget/wall-clock) is a PARTIAL theory, NOT a converged
    result — it is excluded from the metric mean and counted (n_nonconverged/n_timeout/n_maxq)
    so a non-converged fold is never silently averaged as if it converged (H-3). Normal
    convergences (``pool_exhausted``/``empty_bias``/``no_query``, and the blank reason on
    A/C/C∪S) stay in the mean."""
    groups: Dict[tuple, List[dict]] = {}
    for r in rows:
        key = (r['kb'], r['example_set'], r.get('negatives'), r['condition'], r.get('k'))
        groups.setdefault(key, []).append(r)

    out: List[dict] = []
    for (kb, ex, negs, cond, k), grp in groups.items():
        # Truthiness (not key-presence): a merged/blank-filled row may carry error=None on
        # every row; only a real non-None flag marks a failure. (Guards the --merge path.)
        errored = [r for r in grp if r.get('error') is not None or r.get('gate_tripped') is not None]
        # Condition-agnostic: any budget/wall-clock-capped learn (passive QuAcq or QuAcq-active)
        # is a partial theory. A/C/C∪S carry a blank reason, so they are never excluded.
        nonconv = [r for r in grp if r.get('convergence_reason') in ('timeout', 'max_queries')]
        excluded_ids = {id(r) for r in errored} | {id(r) for r in nonconv}
        ok = [r for r in grp if id(r) not in excluded_ids]
        agg = {'kb': kb, 'example_set': ex, 'negatives': negs, 'condition': cond,
               'k': k, 'n_folds': len(grp), 'n_ok_folds': len(ok),
               'n_failed': len(errored),
               'n_nonconverged': len(nonconv),
               'n_timeout': sum(1 for r in nonconv if r.get('convergence_reason') == 'timeout'),
               'n_maxq': sum(1 for r in nonconv if r.get('convergence_reason') == 'max_queries'),
               'n_zero_neg_folds': sum(r.get('zero_neg_train', 0) for r in grp)}
        for col in _AGG_COLS:
            vals = [r[col] for r in ok if r.get(col) is not None]
            if vals:
                agg[f'{col}_mean'] = statistics.mean(vals)
                agg[f'{col}_std'] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        out.append(agg)
    return out
