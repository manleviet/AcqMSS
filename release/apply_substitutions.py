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

    # data/ is OUT OF SCOPE, and that is an assertion rather than a filter. The trees
    # under it are the paper's evidence, and .json is in SUFFIXES, so an unscoped rglob
    # would give a string-rewriting machine write access to the results. No rule matched
    # there today, but that was luck, not design -- and the byte-identical-tables gate
    # cannot see it, because the tables derive from data/results_sosym_r1 alone: rewrite
    # data/examples, data/folds or data/bias and every table still matches.
    all_files = [f for f in out.rglob('*') if f.is_file() and f.suffix in SUFFIXES]
    files = [f for f in all_files if 'data' not in f.relative_to(out).parts[:1]]
    guarded = [f for f in all_files if f not in files]
    hits = {find: 0 for find, _ in rules}
    per_file: dict[str, int] = {}
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
            per_file[str(f.relative_to(out))] = sum(
                orig.count(find) for find, _ in rules if find in orig)

    # Refuse loudly if a rule would have touched the evidence, naming the file. A
    # silent skip would leave the table looking safe while being one edit away from
    # rewriting a result.
    intruders = []
    for f in guarded:
        txt = f.read_text(errors='ignore')
        intruders += [(find, str(f.relative_to(out))) for find, _ in rules if find in txt]
    if intruders:
        print("  a substitution rule matches inside data/, which is the paper's evidence:",
              file=sys.stderr)
        for find, where in intruders[:10]:
            print(f"    {find!r} in {where}", file=sys.stderr)
        print("  Name the specific case and decide deliberately; do not widen the scope.",
              file=sys.stderr)
        return 1

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

    print(f"  {len(rules)} rules, {sum(hits.values())} replacements, 0 residual, "
          f"{len(guarded)} data/ files untouched")
    for f, n in sorted(per_file.items(), key=lambda x: (-x[1], x[0])):
        print(f"      {n:3d}  {f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
