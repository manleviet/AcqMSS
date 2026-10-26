"""Learn A, Reduce(A) and C ∪ S (k = 1) from given training examples through the library path.

Same calls as ``relearn_kbs_with_persistence._conmin_records`` (raw negatives: prepare_task with
minimize=False, ``ConMin.acquire_pool_and_cover``, ``finish_kb`` at k = 1, ``resolve_result``) and,
on the same checker, ConMin's ``Reduce.reduce(ids, [], task.set_b, task.negation_map)`` over A in
the order of ``reduce_a_ablation`` (S_full ∖ C → C → rest of A).
"""
from __future__ import annotations

import conacq.eval.conmin_cv_evaluator as ev
from conacq.algorithms.acqmss.reduce import Reduce

from . import SOLVER, bias_path, fm_path


def learn(kb, tr_pos, tr_neg):
    """Returns names of A / cover / S_full(k=1) / Reduce(A) / C∪S, the C∪S fallback clauses,
    support⁺ per A constraint, the root clauses, and the variable map; None if the
    consistency gate trips."""
    oracle = ev.FMOracle(fm_path(kb), solver_name=SOLVER, use_incremental=True)
    try:
        model = (ev.ConMinModelBuilder.from_bias(bias_path(kb))
                 .with_oracle_data(oracle.oracle_data).build())
        root = [list(c) for c in oracle.oracle_data.get_root_clauses()]
        with ev.profiler_session(ev.ProfilerPreset.BENCHMARK) as prof:
            prepared = model.prepare_task(ev.ConMinTaskInput.from_examples(
                oracle.oracle_data, tr_pos, tr_neg), minimize=False, profiler=prof)
            task, describe = prepared.task, prepared.describe
            checker = ev.build_checker(task, ev.SolverBackend.from_flags(use_incremental=True),
                                       SOLVER, prof)
            try:
                cm = ev.ConMin(checker, prof)
                state = cm.acquire_pool_and_cover(task.set_c, task.set_b, task.set_tc,
                                                  task.set_neg_tv, task.negation_map,
                                                  task.neg_encodings)
                if state is None:
                    return None
                rk = cm.finish_kb(state, task.support_count, 1, task.set_b, task.negation_map)
                _, cs_cl, cs_nm, fb_cl, _ = model.resolve_result(
                    rk, describe, root, task.set_kb, task.negation_map)
                sc = task.support_count or {}
                name = describe.get_description
                a_ids, cover_ids = list(state.mss), list(state.cover_ids)
                cover_set = set(cover_ids)
                s_full_ids = [c for c in a_ids if sc.get(c, 0) >= 1]
                s_full_set = set(s_full_ids)
                order = ([c for c in a_ids if c in s_full_set and c not in cover_set] + cover_ids +
                         [c for c in a_ids if c not in s_full_set and c not in cover_set])
                _, kept = Reduce(checker, prof).reduce(order, [], task.set_b, task.negation_map)
            finally:
                checker.cleanup()
    finally:
        oracle.cleanup()
    to_names = lambda ids: model.resolve_slice(describe, ids)[1]
    return {'A': to_names(a_ids), 'cover': to_names(cover_ids), 'S_full': to_names(s_full_ids),
            'Reduce(A)': to_names(kept), 'C∪S': list(cs_nm),
            'C∪S_fallback': [list(c) for c in fb_cl],
            'support': {name(c): sc.get(c, 0) for c in a_ids},
            'root': root, 'variables': model.name_to_id}
