"""Persisted learned-KB records: one JSON file per (kb, example_set, fold) holding one record
per condition (and per k for C∪S). A record carries everything needed to rebuild the
delivered theory exactly as ``conacq/eval/conmin_slice_scorer.py`` builds it for exact_equiv:
learned bias-constraint names + ¬e⁻ fallback clauses + root clauses.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from . import KB_DIR


def record_path(kb: str, es: str, fold: int) -> Path:
    return KB_DIR / kb / f'{es}_fold{fold}.json'


def save_records(kb: str, es: str, fold: int, records: List[dict]) -> Path:
    path = record_path(kb, es, fold)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(records, indent=1, ensure_ascii=False))
    tmp.replace(path)                      # atomic: a crash never leaves a half file
    return path


def iter_records(kb: Optional[str] = None) -> Iterator[dict]:
    pattern = f'{kb}/*_fold*.json' if kb else '*/*_fold*.json'
    for path in sorted(KB_DIR.glob(pattern)):
        yield from json.loads(path.read_text())


def kb_clauses(record: dict, bias) -> List[List[int]]:
    """Learned clauses resolved from the bias by constraint name (the semantic-tier view)."""
    return [list(c) for cid in record['names'] if bias.has_constraint(cid)
            for c in bias.get_clauses(cid)]


def delivered_theory(record: dict, bias) -> List[List[int]]:
    """slice ∪ ¬e⁻ fallbacks ∪ root — conmin_slice_scorer.py:67-68."""
    return (kb_clauses(record, bias) + [list(c) for c in record['fallback_clauses']]
            + [list(c) for c in record['root_clauses']])


def table5_key(record: dict) -> Dict[str, str]:
    """The (condition, negatives, k) strings make_tables' select() filters on."""
    return {'condition': record['condition'], 'negatives': record['negatives'],
            'k': '' if record['k'] is None else str(record['k'])}
