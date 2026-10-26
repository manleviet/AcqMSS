"""Aggregate the Reduce order ablation: reduce_order.csv (fold × k × order) and the generated
section of reduce_order.md (Table-5-style summary excluding 2-COV, target losses, examples).

usage: python -m apps.conmin_r1.reduce_order_report
"""
from __future__ import annotations

import csv
import json

from pathlib import Path

from conacq.bias import BiasIO
from conacq.oracle.ground_truth import GroundTruthData

from . import K_VALUES, KBS, R1_DIR, bias_path, fm_path
from .dead_features_report import mm, table
from .reduce_a_ablation import OUT_DIR as REDUCE_DIR
from .reduce_a_binned_view import KB_LABEL
from .reduce_order import OUT_DIR

BEGIN, END = '<!-- BEGIN generated -->', '<!-- END generated -->'
SCORE_COLS = ('desc_p', 'desc_r', 'desc_f1', 'clause_p', 'clause_r', 'clause_f1',
              'P_code_bg_empty', 'R_bg_empty', 'F1_code_bg_empty', 'P_std_bg_empty',
              'F1_std_bg_empty', 'P_code_bg_root', 'R_bg_root', 'F1_code_bg_root',
              'P_std_bg_root', 'F1_std_bg_root', 'exact_equiv', 'accuracy',
              'sol_precision', 'sol_recall')


def load():
    folds = []
    for kb in KBS:
        for p in sorted((OUT_DIR / kb).glob('*_fold*.json')):
            f = json.loads(p.read_text())
            f['n_train_pos'] = json.loads(
                (REDUCE_DIR / kb / p.name).read_text())['n_train_pos']
            folds.append(f)
    return folds


def rows(folds):
    out = []
    for f in folds:
        pair = {}
        for r in f['runs']:
            pair.setdefault(r['k'], {})[r['order']] = r
        for r in f['runs']:
            o2 = pair[r['k']]['O2']
            s = r['score']
            removals = len(r['redundant']) if r['order'] == 'O1' else f['n_A'] - f['n_A_prime']
            out.append({
                'kb': f['kb'], 'example_set': f['example_set'], 'fold': f['fold'],
                'n_train_pos': f['n_train_pos'], 'k': r['k'], 'order': r['order'],
                'n_A': f['n_A'], 'n_A_prime': f['n_A_prime'], 'n_kb': len(r['kb']),
                'n_cover': len(r['cover']), 'n_support': len(r['support']),
                'n_fallback': len(r['fallback']), 'reduce_removals': removals,
                'n_target_lost_to_reduce': len(r['target_lost_to_reduce']),
                'n_target_lost_to_reduce_entailed': r['target_lost_to_reduce_entailed'],
                'n_target_lost_to_stage2': len(r['target_lost_to_stage2']),
                'target_lost_to_reduce': '; '.join(r['target_lost_to_reduce']),
                'target_lost_to_stage2': '; '.join(r['target_lost_to_stage2']),
                'cover_differs': int(o2['cover_differs']),
                'n_kb_minus_kb_prime': len(o2['kb_minus_kb_prime']),
                'n_kb_prime_minus_kb': len(o2['kb_prime_minus_kb']),
                'kb_minus_kb_prime': '; '.join(o2['kb_minus_kb_prime']),
                'kb_prime_minus_kb': '; '.join(o2['kb_prime_minus_kb']),
                'reduce_again_removed': '; '.join(r.get('reduce_again_removed_bias', [])),
                'consistent_with_root': s['consistent_with_root'],
                **{c: s.get(c, '') for c in SCORE_COLS}})
    return out


def _vals(rs, col):
    return [float(r[col]) for r in rs if r[col] not in ('', None)]


def summary(rs, k):
    head = ['KB', 'order', 'folds', '\\|KB\\|', '\\|C\\|', '\\|S\\|', 'Reduce removals',
            'desc P', 'desc F1', 'sem P_std', 'sem F1', 'sol P', 'sol R', 'exact_equiv']
    body = []
    for kb in KBS:
        for o in ('O1', 'O2'):
            sel = [r for r in rs if r['kb'] == kb and r['order'] == o and r['k'] == k
                   and r['example_set'] != '2cov']
            ok = [r for r in sel if r['consistent_with_root']]
            note = f' ({len(sel) - len(ok)} UNSAT)' if len(ok) < len(sel) else ''
            body.append([KB_LABEL[kb], o + note, str(len(sel))] +
                        [mm(_vals(sel, c), 1) for c in ('n_kb', 'n_cover', 'n_support',
                                                         'reduce_removals')] +
                        [mm(_vals(ok, c)) for c in ('desc_p', 'desc_f1', 'P_std_bg_root',
                                                     'F1_std_bg_root', 'sol_precision',
                                                     'sol_recall', 'exact_equiv')])
    return table(head, body)


def losses(rs, two_cov):
    head = ['KB', 'k', 'lost to Reduce O1', 'lost to Reduce O2', 'lost to Stage 2 O1',
            'lost to Stage 2 O2', 'entailed / lost (all)', 'C ≠ C′ folds', 'KB ≠ KB′ folds']
    body = []
    for kb in KBS:
        for k in K_VALUES:
            sel = lambda o: [r for r in rs if r['kb'] == kb and r['k'] == k and r['order'] == o
                             and (r['example_set'] == '2cov') == two_cov]
            o1, o2 = sel('O1'), sel('O2')
            if not o1:
                continue
            lost = sum(r['n_target_lost_to_reduce'] for r in o1 + o2)
            ent = sum(r['n_target_lost_to_reduce_entailed'] for r in o1 + o2)
            body.append([KB_LABEL[kb], str(k),
                         mm(_vals(o1, 'n_target_lost_to_reduce'), 1),
                         mm(_vals(o2, 'n_target_lost_to_reduce'), 1),
                         mm(_vals(o1, 'n_target_lost_to_stage2'), 1),
                         mm(_vals(o2, 'n_target_lost_to_stage2'), 1),
                         f'{ent} / {sum(r["n_target_lost_to_reduce_constraints"] if "n_target_lost_to_reduce_constraints" in r else r["n_target_lost_to_reduce"] for r in o1 + o2)}',
                         f"{sum(r['cover_differs'] for r in o2)}/{len(o2)}",
                         f"{sum(r['n_kb_minus_kb_prime'] + r['n_kb_prime_minus_kb'] > 0 for r in o2)}/{len(o2)}"])
    return table(head, body)


def net_targets(folds):
    """Target constructs (description tier) in the FINAL theory, KB′ (O2) minus KB (O1), per fold."""
    head = ['KB'] + [f'k = {k}: Δ mean (median) · O2 fewer / more' for k in K_VALUES]
    body = []
    for kb in KBS:
        bias = BiasIO.load_from_json(bias_path(kb))
        target = GroundTruthData.from_uvl(Path(fm_path(kb))).descriptions
        count = lambda names: len({bias.get_description(n) for n in names} & target)
        cells = []
        for k in K_VALUES:
            d = []
            for f in folds:
                if f['kb'] != kb or f['example_set'] == '2cov':
                    continue
                r = {x['order']: x for x in f['runs'] if x['k'] == k}
                d.append(count(r['O2']['kb']) - count(r['O1']['kb']))
            cells.append(f"{mm(d, 2)} · {sum(x < 0 for x in d)} / {sum(x > 0 for x in d)}")
        body.append([KB_LABEL[kb]] + cells)
    return table(head, body)


def examples(rs, n=4):
    o2 = [r for r in rs if r['order'] == 'O2' and r['example_set'] != '2cov'
          and (r['n_kb_minus_kb_prime'] or r['n_kb_prime_minus_kb'])]
    o2.sort(key=lambda r: -(r['n_kb_minus_kb_prime'] + r['n_kb_prime_minus_kb']))
    seen, out = set(), []
    for r in o2:
        if r['kb'] in seen:
            continue
        seen.add(r['kb'])
        o1 = next(x for x in rs if x['order'] == 'O1' and all(
            x[c] == r[c] for c in ('kb', 'example_set', 'fold', 'k')))
        out.append(f"- **{KB_LABEL[r['kb']]} {r['example_set']} fold {r['fold']}, k = {r['k']}** "
                   f"(n_train_pos {r['n_train_pos']}): |KB| {o1['n_kb']} → |KB′| {r['n_kb']}; "
                   f"cover {'differs' if r['cover_differs'] else 'same'}; desc F1 "
                   f"{float(o1['desc_f1'] or 0):.2f} → {float(r['desc_f1'] or 0):.2f}, sol R "
                   f"{float(o1['sol_recall'] or 0):.3g} → {float(r['sol_recall'] or 0):.3g}.\n"
                   f"  KB ∖ KB′: {r['kb_minus_kb_prime'] or '—'}\n"
                   f"  KB′ ∖ KB: {r['kb_prime_minus_kb'] or '—'}")
        if len(out) == n:
            break
    return '\n'.join(out)


def main():
    folds = load()
    gate_bad = [(f['kb'], f['example_set'], f['fold'], g) for f in folds for g in f['gate']]
    rs = rows(folds)
    with open(R1_DIR / 'reduce_order.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rs[0]))
        w.writeheader()
        w.writerows(rs)
    again = sum(bool(r['reduce_again_removed']) for r in rs if r['order'] == 'O2')
    sec = [BEGIN, '', f'**Gate:** O1 recomputed from the persisted A reproduces the persisted cover '
           f'and the persisted C∪S names and fallbacks on {len(folds)} folds × {len(K_VALUES)} k, '
           f'**{len(gate_bad)} mismatches**. Reduce applied again to C′ ∪ S′ ∪ F′ removed a bias '
           f'constraint in **{again}** of {len(rs) // 2} O2 runs.', '',
           '## Table-5-style summary, k = 1 (excl. 2-COV; mean (median))', '', summary(rs, 1), '']
    for k in K_VALUES[1:]:
        sec += [f'### k = {k}', '', summary(rs, k), '']
    sec += ['## Target constructs lost (per fold; description tier)', '',
            '"Lost to Reduce": target in the pre-Reduce theory (O1: C ∪ S; O2: A), absent after '
            'Reduce (O1: KB; O2: A′). "Lost to Stage 2": target in the Stage-2 pool (O1: A; '
            'O2: A′), absent from C ∪ S. "entailed / lost": lost-to-Reduce target constraints '
            'entailed by the kept theory.', '', '### Table-5 samplings', '',
            losses(rs, False), '', '### 2-COV', '', losses(rs, True), '',
            '## Net target constructs in the final theory (excl. 2-COV)', '',
            'Number of target constructs in KB′ minus in KB, per fold; "fewer / more" counts folds '
            'where Reduce-first keeps fewer / more of them.', '', net_targets(folds), '',
            '## Examples (largest KB ≠ KB′ difference per KB)', '', examples(rs), '', END]
    path = R1_DIR / 'reduce_order.md'
    text = path.read_text() if path.exists() else ''
    body = '\n'.join(sec)
    text = (text[:text.index(BEGIN)] + body + text[text.index(END) + len(END):]
            if BEGIN in text else text.rstrip('\n') + '\n\n' + body + '\n')
    path.write_text(text)
    print(f'gate mismatches {len(gate_bad)}; reduce-again removals {again}; rows {len(rs)}')


if __name__ == '__main__':
    main()
