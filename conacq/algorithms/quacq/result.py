"""
Result data structures for Interactive (QuAcq) constraint acquisition.

Defines QuAcqResult (primary, assumption-ID based) and the legacy
InteractiveResult alias for backward compatibility.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple


@dataclass
class QuAcqResult:
    """
    Result of QuAcq constraint acquisition.

    Captures all information about the learning outcome:
    - Acquired constraints as both assumption IDs and resolved names
    - Query statistics
    - Performance metrics
    - Convergence information
    - Evaluation metrics (optional)

    Attributes:
        kb_assumption_ids: Learned KB as integer assumption IDs (primary)
        kb_constraints:    Learned KB as resolved constraint names (backward compat)
        n_queries:         Total membership queries asked
        n_kb:              Number of constraints in final KB
        convergence_reason: Why learning stopped
        runtime_ms:        Total learning runtime in milliseconds
        consistency_checks: Number of SAT consistency checks performed
        metadata:          Additional metadata for analysis
        query_history:     List of (config, answer, source) triples
        evaluation:        Optional evaluation results
    """
    # Primary: learned KB as assumption IDs
    kb_assumption_ids: List[int] = field(default_factory=list)

    # Resolved constraint names (for backward compat with eval pipeline)
    kb_constraints: List[str] = field(default_factory=list)

    # Query statistics
    n_queries: int = 0
    n_kb: int = 0
    convergence_reason: str = ""
    runtime_ms: float = 0.0
    consistency_checks: int = 0
    metadata: Dict = field(default_factory=dict)

    # Query history: (config, answer, source) triples
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    # Evaluation results (populated after evaluate() is called)
    evaluation: Optional[Dict] = None

    def __post_init__(self):
        """Auto-calculate n_kb if not set."""
        if self.n_kb == 0:
            self.n_kb = len(self.kb_assumption_ids) or len(self.kb_constraints)

    def to_dict(self) -> Dict:
        """Convert result to dictionary for JSON serialization."""
        result = {
            'kb_constraints': self.kb_constraints,
            'kb_assumption_ids': self.kb_assumption_ids,
            'n_queries': self.n_queries,
            'n_kb': self.n_kb,
            'convergence_reason': self.convergence_reason,
            'runtime_ms': self.runtime_ms,
            'consistency_checks': self.consistency_checks,
            'metadata': self.metadata,
            'query_history': [
                {'config': config, 'answer': answer, 'source': source}
                for config, answer, source in self.query_history
            ]
        }
        if self.evaluation is not None:
            result['evaluation'] = self.evaluation
        return result

    def save(self, filepath: str) -> None:
        """Save result to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'QuAcqResult':
        """Load result from JSON file. Handles both old and new formats."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Handle query_history: support 2-tuple (old) and 3-tuple (new) formats
        query_history = []
        for qh in data.get('query_history', []):
            config = qh['config']
            answer = qh['answer']
            source = qh.get('source', 'main')
            query_history.append((config, answer, source))

        return cls(
            kb_assumption_ids=data.get('kb_assumption_ids', []),
            kb_constraints=data.get('kb_constraints', []),
            n_queries=data.get('n_queries', 0),
            n_kb=data.get('n_kb', 0),
            convergence_reason=data.get('convergence_reason', ''),
            runtime_ms=data.get('runtime_ms', 0.0),
            consistency_checks=data.get('consistency_checks', 0),
            metadata=data.get('metadata', {}),
            query_history=query_history,
            evaluation=data.get('evaluation')
        )

    def __repr__(self):
        return (f"QuAcqResult(n_kb={self.n_kb}, n_queries={self.n_queries}, "
                f"convergence='{self.convergence_reason}')")


# Backward-compat alias
InteractiveResult = QuAcqResult
