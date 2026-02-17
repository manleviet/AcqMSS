"""
Result data structures for Interactive (QuAcq) constraint acquisition.

Defines the InteractiveResult that captures the outcome of interactive learning.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple


@dataclass
class InteractiveResult:
    """
    Result of interactive constraint acquisition.

    Captures all information about the learning outcome:
    - Acquired constraints
    - Query statistics
    - Performance metrics
    - Convergence information
    - Evaluation metrics (optional)

    Attributes:
        kb_constraints: List of learned constraint IDs
        n_queries: Total number of membership queries asked
        n_kb: Number of constraints in final KB
        convergence_reason: Why learning stopped ('empty_bias', 'max_queries', 'no_query')
        runtime_ms: Total learning runtime in milliseconds
        consistency_checks: Number of SAT consistency checks performed
        metadata: Additional metadata for analysis
        evaluation: Optional evaluation results with both strategies
            {
                'description': EvaluationResult dict,  # Strategy 1
                'clause': EvaluationResult dict,       # Strategy 2
            }
    """
    # Learned constraint IDs
    kb_constraints: List[str] = field(default_factory=list)

    # Query statistics
    n_queries: int = 0

    # Size of final KB
    n_kb: int = 0

    # Why learning converged
    convergence_reason: str = ""

    # Runtime in milliseconds
    runtime_ms: float = 0.0

    # Number of consistency checks
    consistency_checks: int = 0

    # Additional metadata
    metadata: Dict = field(default_factory=dict)

    # Query history for analysis: list of (config_dict, oracle_answer)
    query_history: List[Tuple[Dict[str, bool], bool]] = field(default_factory=list)

    # Evaluation results (optional, populated after evaluate() is called)
    evaluation: Optional[Dict] = None

    def __post_init__(self):
        """Update n_kb from kb_constraints if not set."""
        if self.n_kb == 0 and self.kb_constraints:
            self.n_kb = len(self.kb_constraints)

    def to_dict(self) -> Dict:
        """Convert result to dictionary for serialization."""
        result = {
            'kb_constraints': self.kb_constraints,
            'n_queries': self.n_queries,
            'n_kb': self.n_kb,
            'convergence_reason': self.convergence_reason,
            'runtime_ms': self.runtime_ms,
            'consistency_checks': self.consistency_checks,
            'metadata': self.metadata,
            'query_history': [
                {'config': config, 'answer': answer}
                for config, answer in self.query_history
            ]
        }
        if self.evaluation is not None:
            result['evaluation'] = self.evaluation
        return result

    def save(self, filepath: str) -> None:
        """
        Save result to JSON file.

        Args:
            filepath: Output file path
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'InteractiveResult':
        """
        Load result from JSON file.

        Args:
            filepath: Input file path

        Returns:
            InteractiveResult instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Convert query history back to tuple format
        query_history = [
            (qh['config'], qh['answer'])
            for qh in data.get('query_history', [])
        ]

        return cls(
            kb_constraints=data['kb_constraints'],
            n_queries=data['n_queries'],
            n_kb=data['n_kb'],
            convergence_reason=data['convergence_reason'],
            runtime_ms=data['runtime_ms'],
            consistency_checks=data.get('consistency_checks', 0),
            metadata=data.get('metadata', {}),
            query_history=query_history,
            evaluation=data.get('evaluation')
        )

    def __repr__(self):
        return (f"InteractiveResult(n_kb={self.n_kb}, n_queries={self.n_queries}, "
                f"convergence='{self.convergence_reason}')")
