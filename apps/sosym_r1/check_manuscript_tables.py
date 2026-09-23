#!/usr/bin/env python3
"""Hold the manuscript's printed tables to the generated fragments.

    python3 apps/sosym_r1/check_manuscript_tables.py <path to main-r1.tex>

DEVELOPMENT-SIDE ONLY. It is not in the artifact's keep-list and never will be: the
argument it needs is a manuscript, and the artifact has none. Running it there would
mean shipping the paper, which is a different decision from shipping the code that
produced its numbers.

WHY IT EXISTS
-------------
`check_paper_tables.py` re-derives every cell of every FRAGMENT from the committed
results. Nothing held the manuscript to the fragment, because the journal's template
forbids `\\input` of other TeX files, so the manuscript carries a TRANSCRIPTION. That
left one link unchecked in a chain that is otherwise checked end to end: a typo made
while copying a fragment into the paper would reach a reader through a gate that was
green the whole way.

WHAT IT COMPARES
----------------
Rows, after normalising whitespace around separators and dropping comments and rules,
plus the column specification. Not the caption, the label or the table environment:
those are editorial and live in the manuscript by design.

A fragment with no table in the manuscript is reported as **not printed** and is not a
failure IF it is declared below. Exactly one is: the significance fragment, which the
2026-09-23 review moved into prose. An undeclared absence is a failure, because the
common way for a table to vanish from a paper is that somebody deleted it by accident.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRAGMENTS = REPO / 'data' / 'results_sosym_r1' / 'tables' / 'paper'
# Fragments the artifact keeps although the paper prints no such table.
NOT_PRINTED = {'tab_significance'}

_RULES = ('\\toprule', '\\midrule', '\\bottomrule', '\\cmidrule',
          '\\begin{tabular}', '\\end{tabular}')


def rows_of(block: str) -> list[str]:
    """The rows of one tabular, whitespace-normalised; comments and rules dropped."""
    out = []
    for line in block.splitlines():
        s = line.strip()
        if not s or s.startswith('%') or s.startswith(_RULES):
            continue
        out.append(re.sub(r'\s+', ' ', re.sub(r'\s*&\s*', ' & ', s)).strip())
    return out


def colspec(block: str) -> str:
    m = re.search(r'\\begin\{tabular\}\{([^}]*)\}', block)
    return m.group(1) if m else '?'


def tables_in(manuscript: Path) -> dict[str, str]:
    """Every tabular in the manuscript, keyed by the label that precedes it."""
    text = manuscript.read_text()
    found = {}
    for m in re.finditer(r'\\begin\{tabular\}.*?\\end\{tabular\}', text, re.S):
        labels = re.findall(r'\\label\{(tab:[^}]+)\}', text[:m.start()])
        if labels:
            found[labels[-1]] = m.group(0)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('manuscript', help='path to main-r1.tex')
    ap.add_argument('--fragments', default=str(FRAGMENTS))
    args = ap.parse_args()

    printed = tables_in(Path(args.manuscript))
    fragments = sorted(Path(args.fragments).glob('*.tex'))
    if not fragments:
        print(f'FAIL: no fragments under {args.fragments}', file=sys.stderr)
        return 1

    bad = []
    for path in fragments:
        name = path.stem
        label = 'tab:' + name[len('tab_'):]
        frag = path.read_text()
        if label not in printed:
            if name in NOT_PRINTED:
                print(f'  {name:32s} not printed (declared artifact-only)')
            else:
                print(f'  {name:32s} NO TABLE LABELLED {label}')
                bad.append(name)
            continue
        want, got = rows_of(printed[label]), rows_of(frag)
        same = want == got and colspec(printed[label]) == colspec(frag)
        print(f'  {name:32s} {"identical" if same else "DIFFERS"} '
              f'({len(got)} rows, spec {colspec(frag)})')
        if same:
            continue
        bad.append(name)
        for line in list(difflib.unified_diff(want, got, 'manuscript', 'fragment',
                                              lineterm='', n=0))[:12]:
            print(f'      {line[:160]}')

    # A positive count: an empty comparison would otherwise print nothing and exit 0.
    print(f'\n{len(fragments)} fragment(s) compared, {len(bad)} not matching the paper')
    if bad:
        print('\nThe manuscript is transcribed by hand, so a mismatch is a typo in the\n'
              'paper or a fragment the paper has not caught up with. Fix whichever is\n'
              'behind -- never this comparison.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
