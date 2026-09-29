#!/usr/bin/env python
"""Raw vs reduced negative examples in ConGen: per fold, per cell, at printed precision.

Reads the committed (reduced) tree and a raw re-run (run_ne_raw_sweep.py, then scored
by run_compare through make_score_configs.py exactly as Table 14 was) and tests four
predictions derived from the code:

  P1  B' (AcqMss output) is identical per fold. B' is read as the SET
      kb_constraints ∪ redundant_constraints -- Reduce partitions B' into the two, and
      |B'| == n_mss is checked as a control on both sides. AcqMss's own check count
      (profiler.paper_consistency_checks) is compared too: equal counts on an
      identical B' mean the same recursion, not just the same answer.
  P2  on folds whose committed n_ne == 0, the final KB is identical (list equality,
      order included).
  P3  on folds whose committed n_ne == 1, the KB may differ; each difference is listed.
  P4  under raw NE, KB ∪ NE ∪ root rejects every TRAINING e⁻ of the fold. The theory
      is rebuilt from the fold record, and the rebuild is CONTROLLED: it must reproduce
      the fold's recorded test accuracy, or the fold is reported and nothing is claimed.

Cell values are MEANS OVER FOLDS and are rendered with the paper generator's own
formatters (paper_tables/latex.py), so "a printed value changes" means the string in
the table would change. Raw GenerateNE never calls QuickXplain, so its preprocessing
counters are never created; they are read as 0 only after asserting the fold is raw.

    compare_ne_raw_vs_reduced.py --raw data/results_sosym_r1_rawne/congen \\
        --json data/results_sosym_r1_rawne/raw-vs-reduced.json
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from apps.sosym_r1.paper_tables import latex as tex                          # noqa: E402
from conacq.algorithms.acqmss.congen_model_builder import ConGenModelBuilder  # noqa: E402
from conacq.eval import apply_folds, load_folds                              # noqa: E402
from conacq.eval.accuracy import AccuracyCalculator                          # noqa: E402
from conacq.examples import ExampleIO                                        # noqa: E402
from conacq.oracle import FMOracle                                           # noqa: E402
from pysat.solvers import Solver                                             # noqa: E402

STEMS = ['busybox-1.18.0', 'arcade-game', 'REAL-FM-7', 'REAL-FM-4', 'fqa']
PREP = 'shared_preprocessing_quickxplain_checks'


def ids(entries):
    return [c['id'] if isinstance(c, dict) else c for c in entries]


def tier(fold, name, key):
    return (((fold.get('evaluation') or {}).get(name) or {}).get('metrics') or {}).get(key)


def fold_values(f: dict, raw: bool) -> dict:
    prof, perf = f['performance']['profiler'], f['performance']
    if raw:
        assert PREP not in prof or prof[PREP] == 0, 'raw fold ran QuickXplain'
    prep = prof.get(PREP, 0) if raw or f['train_size']['negative'] else 0
    if not raw and f['train_size']['negative'] and PREP not in prof:
        raise KeyError(f"reduced fold {f['fold_index']} with negatives lacks {PREP}")
    acq, red = prof['paper_consistency_checks'], perf['redundancy_consistency_checks']
    return {'acc': f['accuracy'], 'kb': len(f['kb_constraints']),
            'n_ne': f['statistics']['n_ne'], 'n_mss': f['statistics']['n_mss'],
            'sem_p': tier(f, 'semantic', 'precision'), 'sem_r': tier(f, 'semantic', 'recall'),
            'sem_f1': tier(f, 'semantic', 'f1_score'),
            'clause_f1': tier(f, 'clause', 'f1_score'),
            'desc_f1': tier(f, 'description', 'f1_score'),
            'acq_checks': acq, 'red_checks': red, 'prep_checks': prep,
            'total_checks': acq + red + prep, 'runtime_ms': perf['runtime_ms']}


# (key, formatter, table) -- the printed column each quantity lands in.
PRINTED = [('acc', tex.quality, 'T13'), ('kb', tex.one_decimal, 'T13'),
           ('sem_p', tex.quality, 'T14'), ('sem_r', tex.quality, 'T14'),
           ('sem_f1', tex.quality, 'T14'), ('clause_f1', tex.quality, 'T12'),
           ('desc_f1', tex.quality, 'T12'), ('n_ne', tex.one_decimal, '-'),
           ('prep_checks', tex.count, 'T9'), ('total_checks', tex.count, 'T9'),
           ('runtime_ms', tex.millis, 'T9')]


def entails(theory: list, clauses: list) -> bool:
    """theory |= every clause: theory AND NOT(clause) is UNSAT for each one."""
    with Solver(name='glucose4', bootstrap_with=theory) as sat:
        return not any(sat.solve(assumptions=[-lit for lit in cl]) for cl in clauses)


def explain_difference(model_kb, fr: dict, fd: dict) -> dict:
    """Why the two KBs differ, by entailment rather than by narrative.

    Reduce's BG is EMPTY for a feature model: the root is kept out of acquisition and
    re-added at delivery. So a constraint one side kept and the other dropped is
    classified against the OTHER side, in Reduce's own view first (no root):

      order    entailed by the other bias KB alone -- another representative of the
               same theory was kept (Reduce is order-dependent)
      ne       entailed only once the other side's surviving ¬e⁻ is added -- Reduce
               dropped it because that memorized fact entails it
      root     entailed only once the root axiom is also added (not a reason Reduce
               could have used; the delivered theories still agree on it)
      absent   not entailed even by the other delivered theory -- a semantic change

    Also: whether each delivered theory (bias + ¬e⁻ + root) entails the other, and
    whether each side's surviving ¬e⁻ is literally the root axiom."""
    def bias(fold):
        return [list(c) for cid in ids(fold['kb_constraints'])
                for c in model_kb.constraint_map.get(cid, ())]

    def ne(fold):
        return [list(c) for c in fold['ne_clauses']]

    def root(fold):
        return [list(c) for c in fold['bg_clauses']]

    def why(cid, other):
        cl = [list(c) for c in model_kb.constraint_map[cid]]
        if entails(bias(other), cl):
            return 'order'
        if entails(bias(other) + ne(other), cl):
            return 'ne'
        if entails(bias(other) + ne(other) + root(other), cl):
            return 'root'
        return 'absent'

    kb_r, kb_d = ids(fr['kb_constraints']), ids(fd['kb_constraints'])
    delivered = lambda f: bias(f) + ne(f) + root(f)  # noqa: E731
    return {'only_raw_why': {c: why(c, fd) for c in kb_r if c not in kb_d},
            'only_reduced_why': {c: why(c, fr) for c in kb_d if c not in kb_r},
            'raw_entails_reduced': entails(delivered(fr), delivered(fd)),
            'reduced_entails_raw': entails(delivered(fd), delivered(fr)),
            'ne_is_root_raw': bool(ne(fr)) and all(c in root(fr) for c in ne(fr)),
            'ne_is_root_reduced': bool(ne(fd)) and all(c in root(fd) for c in ne(fd))}


def rejects_training_negatives(stem, model, fold, model_kb) -> tuple[bool, bool, int]:
    """(control_ok, all training e⁻ rejected, #training e⁻) for one raw fold."""
    ex = ExampleIO.load_json(str(REPO / 'data' / 'examples' / f'{model}.json'))
    pos = [e.assignments for e in ex.positive]
    neg = [e.assignments for e in ex.negative]
    fd = load_folds(str(REPO / 'data' / 'folds' / f'{model}_folds.json'))
    _, tr_neg, te_pos, te_neg = apply_folds(fd, pos, neg, fold['fold_index'])
    theory = ([list(c) for cid in ids(fold['kb_constraints'])
               for c in model_kb.constraint_map.get(cid, ())]
              + [list(c) for c in fold['ne_clauses']] + [list(c) for c in fold['bg_clauses']])
    with AccuracyCalculator(theory, model_kb.name_to_id, 'glucose4') as calc:
        control = abs(calc.calculate(te_pos, te_neg).metrics.accuracy
                      - fold['accuracy']) < 1e-9
        m = calc.calculate([], tr_neg).metrics
    return control, m.false_positives == 0, len(tr_neg)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--raw', required=True, help='raw congen dir (scored CV files)')
    ap.add_argument('--reduced', default=str(REPO / 'data/results_sosym_r1/congen'))
    ap.add_argument('--json', required=True, help='where to write the full comparison')
    args = ap.parse_args()

    folds_out, cells_out = [], []
    for raw_cv in sorted(Path(args.raw).glob('*_cv_incremental.json')):
        model = raw_cv.name.split('_cv_')[0]
        stem = next(s for s in STEMS if model.startswith(s + '_'))
        raw_doc = json.loads(raw_cv.read_text())
        red_doc = json.loads((Path(args.reduced) / raw_cv.name).read_text())
        oracle = FMOracle(str(REPO / 'data/fms' / f'{stem}.uvl'), use_incremental=False)
        try:
            model_kb = (ConGenModelBuilder.from_bias(str(REPO / 'data/bias' / f'{stem}-bias.json'))
                        .with_oracle_data(oracle.oracle_data).build())
            per = {'raw': [], 'red': []}
            for fr, fd in zip(raw_doc['folds'], red_doc['folds']):
                assert fr['fold_index'] == fd['fold_index']
                vr, vd = fold_values(fr, True), fold_values(fd, False)
                per['raw'].append(vr)
                per['red'].append(vd)
                bp_r = set(ids(fr['kb_constraints'])) | set(fr['redundant_constraints'])
                bp_d = set(ids(fd['kb_constraints'])) | set(fd['redundant_constraints'])
                kb_r, kb_d = ids(fr['kb_constraints']), ids(fd['kb_constraints'])
                desc = {c['id']: c['description'] for c in fr['kb_constraints'] + fd['kb_constraints']
                        if isinstance(c, dict)}
                control, p4, n_tr = rejects_training_negatives(stem, model, fr, model_kb)
                folds_out.append({
                    'model': model, 'fold': fr['fold_index'],
                    'train_neg': fr['train_size']['negative'],
                    'bprime_control': len(bp_r) == vr['n_mss'] and len(bp_d) == vd['n_mss'],
                    'bprime_equal': bp_r == bp_d,
                    'acq_checks_equal': vr['acq_checks'] == vd['acq_checks'],
                    'kb_equal_ordered': kb_r == kb_d, 'kb_equal_set': set(kb_r) == set(kb_d),
                    'only_raw': [f'{c}: {desc.get(c, "")}' for c in kb_r if c not in kb_d],
                    'only_reduced': [f'{c}: {desc.get(c, "")}' for c in kb_d if c not in kb_r],
                    'ne_raw': fr['ne_constraints'], 'ne_reduced': fd['ne_constraints'],
                    'why': (None if kb_r == kb_d else explain_difference(model_kb, fr, fd)),
                    'p4_control': control, 'p4_rejects_all': p4, 'p4_n_train_neg': n_tr,
                    'raw': vr, 'reduced': vd})
        finally:
            oracle.cleanup()

        cell = {'model': model, 'changed': []}
        for key, fmt, table in PRINTED:
            for side in ('raw', 'red'):
                vals = [v[key] for v in per[side] if v[key] is not None]
                cell[f'{key}_{side}'] = st.mean(vals) if vals else None
            a, b = fmt(cell[f'{key}_raw']), fmt(cell[f'{key}_red'])
            cell[f'{key}_printed'] = (a, b)
            if a != b and table != '-':
                cell['changed'].append(f'{table} {key}: {b} -> {a}')
        cells_out.append(cell)

    Path(args.json).write_text(json.dumps({'folds': folds_out, 'cells': cells_out},
                                          indent=1))
    n = len(folds_out)
    count = lambda k: sum(1 for f in folds_out if f[k])  # noqa: E731
    print(f"folds {n}   B' control {count('bprime_control')}/{n}   "
          f"P1 B' equal {count('bprime_equal')}/{n}   "
          f"AcqMss checks equal {count('acq_checks_equal')}/{n}")
    for label, want in (('P2 (reduced n_ne=0)', 0), ('P3 (reduced n_ne=1)', 1)):
        sub = [f for f in folds_out if f['reduced']['n_ne'] == want]
        print(f"{label}: {len(sub)} folds, KB identical (ordered) "
              f"{sum(f['kb_equal_ordered'] for f in sub)}, as set "
              f"{sum(f['kb_equal_set'] for f in sub)}")
    print(f"P4 control {count('p4_control')}/{n}   rejects all training e- "
          f"{count('p4_rejects_all')}/{n}")
    print(f"cells with a printed change: {sum(1 for c in cells_out if c['changed'])}"
          f"/{len(cells_out)}")
    return 0 if all(f['bprime_control'] and f['p4_control'] for f in folds_out) else 1


if __name__ == '__main__':
    sys.exit(main())
