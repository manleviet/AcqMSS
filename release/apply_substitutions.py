#!/usr/bin/env python3
"""Apply a target's phrase-substitution table to a carved tree.

    apply_substitutions.py <carved-dir> <substitutions-file>

Phrase substitutions rather than context diffs, because these are one-phrase edits
scattered across twenty comments: as diffs they would break whenever someone edits a
neighbouring line upstream, and a mechanism that fails when a colleague writes a good
comment is the wrong mechanism.

Two assertions, both of which must hold:

  * every rule matches at least once -- a rule matching nothing means the upstream
    wording moved and this table is stale, which is silent rot rather than a no-op;
  * no `find` string survives -- a positive replacement count, then zero residue.

Together they make this step report a number rather than an absence.
"""
from __future__ import annotations

import pathlib
import sys

SUFFIXES = {'.py', '.md', '.toml', '.json', '.sh', '.cff'}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    out, table = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])

    rules: list[tuple[str, str]] = []
    for line in table.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        find, sep, repl = line.partition('\t')
        if not sep:
            print(f"  malformed rule (no tab): {line!r}", file=sys.stderr)
            return 1
        rules.append((find, repl))
    if not rules:
        print("  substitution table is empty", file=sys.stderr)
        return 1

    files = [f for f in out.rglob('*') if f.is_file() and f.suffix in SUFFIXES]
    hits = {find: 0 for find, _ in rules}
    for f in files:
        try:
            txt = orig = f.read_text(errors='ignore')
        except Exception:
            continue
        for find, repl in rules:
            if find in txt:
                hits[find] += txt.count(find)
                txt = txt.replace(find, repl)
        if txt != orig:
            f.write_text(txt)

    dead = [find for find, n in hits.items() if n == 0]
    if dead:
        print("  rules that matched nothing -- upstream wording moved, table is stale:",
              file=sys.stderr)
        for d in dead:
            print(f"    {d!r}", file=sys.stderr)
        return 1

    survivors = []
    for f in files:
        txt = f.read_text(errors='ignore')
        survivors += [(find, str(f)) for find, _ in rules if find in txt]
    if survivors:
        print(f"  {len(survivors)} occurrence(s) survived substitution:", file=sys.stderr)
        for find, where in survivors[:10]:
            print(f"    {find!r} in {where}", file=sys.stderr)
        return 1

    print(f"  {len(rules)} rules, {sum(hits.values())} replacements, 0 residual")
    return 0


if __name__ == '__main__':
    sys.exit(main())
