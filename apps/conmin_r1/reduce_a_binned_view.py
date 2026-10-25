"""Reduce(A) vs ConMin under positive scarcity: Table-5 folds in thirds of n_train_pos, and
the 2-COV folds (0–1 positives).

Thirds are within each KB: its 15 Table-5 folds sorted by (n_train_pos, example_set, fold),
5 per third. Stage 2's share of the A → ConMin change = (Reduce(A) − ConMin) / (A − ConMin),
on the means, for |KB| and sem P_std. A share whose denominator |A − ConMin| < SHARE_EPS is
flagged as near-zero-denominator (it carries no information). Called by
``reduce_a_ablation_report``; writes the generated section of ``reduce_a_ablation.md``
between the BEGIN/END markers.
"""
from __future__ import annotations

from . import KBS, R1_DIR
from .reduce_a_ablation_report import CONDS, summary_entry

SHARE_EPS = 0.01
THIRDS = ('low', 'mid', 'high')
KB_LABEL = {'REAL-FM-7': 'KB₁', 'fqa': 'KB₂', 'arcade-game': 'KB₃', 'REAL-FM-4': 'KB₄'}
BEGIN, END = '<!-- BEGIN binned view (generated) -->', '<!-- END binned view (generated) -->'


def _share(a, red, conmin):
    if '' in (a, red, conmin):
        return '', 'undefined'
    a, red, conmin = float(a), float(red), float(conmin)
    if abs(a - conmin) < SHARE_EPS:
        return '', f'near-zero denominator (|A − ConMin| = {abs(a - conmin):.3f})'
    return round((red - conmin) / (a - conmin), 4), ''


def binned_entries(rows):
    out = []
    for kb in KBS:
        keys = sorted({(int(r['n_train_pos']), r['example_set'], int(r['fold']))
                       for r in rows if r['kb'] == kb and r['example_set'] != '2cov'})
        for i, third in enumerate(THIRDS):
            part = keys[5 * i:5 * i + 5]
            members = {(es, f) for _, es, f in part}
            label = f'Table 5 third {third} (n_train_pos {part[0][0]}–{part[-1][0]})'
            entries = {c: summary_entry(
                [r for r in rows if r['kb'] == kb and r['condition'] == c
                 and (r['example_set'], int(r['fold'])) in members], kb, c, label)
                for c in CONDS}
            shares = {}
            for col in ('n_kb', 'P_std_bg_root'):
                shares[col] = _share(*(entries[c][f'{col}_mean'] for c in CONDS))
            for c in CONDS:
                entries[c].update({
                    'third': third, 'n_train_pos_range': f'{part[0][0]}–{part[-1][0]}',
                    'stage2_share_n_kb': shares['n_kb'][0],
                    'stage2_share_P_std': shares['P_std_bg_root'][0],
                    'share_note': '; '.join(n for n in (shares['n_kb'][1],
                                                        shares['P_std_bg_root'][1]) if n)})
                out.append(entries[c])
    return out


def _g(v, d=2):
    if v in ('', None):
        return '—'
    x = float(v)
    return f'{x:.2g}' if 0 < abs(x) < 0.01 else f'{x:.{d}f}'


def _pct(v):
    return '—' if v in ('', None) else f'{float(v):.0%}'


def _table(entries, with_share):
    cols = ['KB', 'n_train_pos', 'condition', '\\|KB\\|', 'sem P_std', 'sem F1',
            'sol P mean (median)', 'sol R mean (median)', '\\|V kept\\|']
    if with_share:
        cols.append('Stage 2 share \\|KB\\| / P_std')
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    notes = []
    for e in entries:
        if e['condition'] == 'A':
            continue
        share = ''
        if with_share:
            if e['condition'] == 'ConMin k=1':      # one share per third, on the ConMin row
                mark = ''
                if e['share_note']:
                    notes.append(f"{KB_LABEL[e['kb']]} {e['third']}: {e['share_note']}")
                    mark = '†'
                share = (f" {_pct(e['stage2_share_n_kb'])} / "
                         f"{_pct(e['stage2_share_P_std'])}{mark} |")
            else:
                share = ' |'
        rng = e['n_train_pos_range']
        lines.append(
            f"| {KB_LABEL[e['kb']]}{' ' + e['third'] if with_share else ''} | {rng} | "
            f"{e['condition']} {e['note']} | {_g(e['n_kb_mean'], 1)} | "
            f"{_g(e['P_std_bg_root_mean'])} | {_g(e['F1_std_bg_root_mean'])} | "
            f"{_g(e['sol_precision_mean'])} ({_g(e['sol_precision_median'])}) | "
            f"{_g(e['sol_recall_mean'])} ({_g(e['sol_recall_median'])}) | "
            f"{_g(e['V_kept_mean'], 1)} |{share}")
    if notes:
        lines += ['', '† not reported — ' + '; '.join(notes) + '.']
    return '\n'.join(lines)


def write_markdown_section(summary):
    two_cov = [e for e in summary if e['sampling'] == '2-COV']
    thirds = [e for e in summary if 'third' in e]
    section = '\n'.join([
        BEGIN, '', '## Positive scarcity: Reduce(A) vs ConMin (k = 1)', '',
        'Means over folds; sol P / sol R also as median (ratios span orders of magnitude). '
        'sem = root as background, P_std, F1 with P_std. UNSAT folds counted, not scored.', '',
        '### 2-COV folds (0–1 training positives)', '', _table(two_cov, False), '',
        '### Table-5 folds by thirds of n_train_pos (within KB, 5 folds each)', '',
        "Stage 2 share = (Reduce(A) − ConMin) / (A − ConMin) on the means. A share whose "
        f"denominator |A − ConMin| < {SHARE_EPS} is not reported (near-zero denominator).",
        '', _table(thirds, True), '', END])
    path = R1_DIR / 'reduce_a_ablation.md'
    text = path.read_text()
    if BEGIN in text:
        text = text[:text.index(BEGIN)] + section + text[text.index(END) + len(END):]
    else:
        text = text.rstrip('\n') + '\n\n' + section + '\n'
    path.write_text(text)
