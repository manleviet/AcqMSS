"""
Metrics for comparing CONGEN (passive) vs QuAcq (interactive) learning.

Provides utilities for:
- Computing query efficiency metrics
- Comparing KB quality between approaches
- Generating Table 12 style comparison reports
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .evaluator import Evaluator, EvaluationStrategy
from .result_loader import CONGENResultData


@dataclass
class InteractiveMetrics:
    """
    Metrics for interactive constraint acquisition.

    Captures both learning efficiency and KB quality.

    Attributes:
        n_queries: Number of membership queries asked
        n_kb: Size of learned KB
        accuracy: Accuracy of learned KB
        precision: Precision of learned KB
        recall: Recall of learned KB
        f1_score: F1 score of learned KB
        runtime_ms: Total learning runtime
        convergence_reason: Why learning stopped
    """
    n_queries: int = 0
    n_kb: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    runtime_ms: float = 0.0
    convergence_reason: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'n_queries': self.n_queries,
            'n_kb': self.n_kb,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'runtime_ms': self.runtime_ms,
            'convergence_reason': self.convergence_reason,
            'metadata': self.metadata
        }


@dataclass
class CONGENMetrics:
    """
    Metrics for CONGEN (passive) constraint acquisition.

    Attributes:
        n_examples: Total number of examples (|E+| + |E-|)
        n_positive: Number of positive examples
        n_negative: Number of negative examples
        n_kb: Size of learned KB
        accuracy: Accuracy of learned KB
        precision: Precision of learned KB
        recall: Recall of learned KB
        f1_score: F1 score of learned KB
        runtime_ms: Total learning runtime
        sampling_strategy: Sampling strategy used
    """
    n_examples: int = 0
    n_positive: int = 0
    n_negative: int = 0
    n_kb: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    runtime_ms: float = 0.0
    sampling_strategy: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'n_examples': self.n_examples,
            'n_positive': self.n_positive,
            'n_negative': self.n_negative,
            'n_kb': self.n_kb,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'runtime_ms': self.runtime_ms,
            'sampling_strategy': self.sampling_strategy,
            'metadata': self.metadata
        }


@dataclass
class ComparisonResult:
    """
    Comparison between CONGEN and QuAcq results.

    Attributes:
        model_name: Name of the model
        congen: CONGEN metrics
        quacq: QuAcq metrics
        query_efficiency: Ratio of CONGEN examples to QuAcq queries
        accuracy_diff: QuAcq accuracy - CONGEN accuracy
        kb_size_diff: QuAcq KB size - CONGEN KB size
    """
    model_name: str
    congen: CONGENMetrics
    quacq: InteractiveMetrics

    @property
    def query_efficiency(self) -> float:
        """
        Query efficiency = CONGEN examples / QuAcq queries.

        Higher means QuAcq is more efficient (needs fewer queries).
        """
        if self.quacq.n_queries == 0:
            return float('inf')
        return self.congen.n_examples / self.quacq.n_queries

    @property
    def accuracy_diff(self) -> float:
        """QuAcq accuracy - CONGEN accuracy."""
        return self.quacq.accuracy - self.congen.accuracy

    @property
    def kb_size_diff(self) -> int:
        """QuAcq KB size - CONGEN KB size."""
        return self.quacq.n_kb - self.congen.n_kb

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'model_name': self.model_name,
            'congen': self.congen.to_dict(),
            'quacq': self.quacq.to_dict(),
            'comparison': {
                'query_efficiency': self.query_efficiency,
                'accuracy_diff': self.accuracy_diff,
                'kb_size_diff': self.kb_size_diff
            }
        }


class InteractiveEvaluator:
    """
    Evaluator for interactive constraint acquisition.

    Computes metrics for QuAcq results and compares with CONGEN.
    """

    def __init__(self, oracle_path: str, bias_path: str):
        """
        Initialize evaluator.

        Args:
            oracle_path: Path to feature model for ground truth
            bias_path: Path to bias JSON file
        """
        self.oracle_path = Path(oracle_path)
        self.bias_path = Path(bias_path)
        self.evaluator = Evaluator.from_files(self.oracle_path, self.bias_path)

    def evaluate_interactive_result(
            self,
            result_path: str,
            strategy: EvaluationStrategy = EvaluationStrategy.DESCRIPTION
    ) -> InteractiveMetrics:
        """
        Evaluate an interactive learning result.

        Args:
            result_path: Path to interactive result JSON
            strategy: Evaluation strategy (DESCRIPTION or CLAUSE)

        Returns:
            InteractiveMetrics with accuracy computed
        """
        with open(result_path, 'r') as f:
            result_data = json.load(f)

        # Get KB constraint IDs
        kb_constraints = result_data.get('kb_constraints', [])

        # Create CONGENResultData-like object for evaluation
        congen_result = CONGENResultData(
            kb_constraints=kb_constraints,
            redundant_constraints=[],
            n_bias=len(self.evaluator.bias.constraints),
            n_mss=0,
            n_kb=result_data.get('n_kb', len(kb_constraints)),
            bg_clauses=result_data.get('bg_clauses', [])
        )

        # Evaluate using specified strategy
        eval_result = self.evaluator.evaluate(congen_result, strategy)
        metrics = eval_result.metrics

        return InteractiveMetrics(
            n_queries=result_data.get('n_queries', 0),
            n_kb=result_data.get('n_kb', 0),
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1_score=metrics.f1_score,
            runtime_ms=result_data.get('runtime_ms', 0.0),
            convergence_reason=result_data.get('convergence_reason', ''),
            metadata=result_data.get('metadata', {})
        )

    def evaluate_both_strategies(
            self,
            result_path: str
    ) -> Dict[str, InteractiveMetrics]:
        """
        Evaluate an interactive learning result using both strategies.

        Args:
            result_path: Path to interactive result JSON

        Returns:
            Dictionary with metrics for both strategies:
            {
                'description': InteractiveMetrics,  # Strategy 1
                'clause': InteractiveMetrics,       # Strategy 2
            }
        """
        desc_metrics = self.evaluate_interactive_result(
            result_path,
            EvaluationStrategy.DESCRIPTION
        )
        clause_metrics = self.evaluate_interactive_result(
            result_path,
            EvaluationStrategy.CLAUSE
        )

        return {
            'description': desc_metrics,
            'clause': clause_metrics
        }

    def evaluate_congen_result(
            self,
            result_path: str,
            examples_path: str
    ) -> CONGENMetrics:
        """
        Evaluate a CONGEN result.

        Args:
            result_path: Path to CONGEN result JSON
            examples_path: Path to examples JSON

        Returns:
            CONGENMetrics with accuracy computed
        """
        with open(result_path, 'r') as f:
            result_data = json.load(f)

        with open(examples_path, 'r') as f:
            examples = json.load(f)

        # Get KB constraints
        kb_constraints = result_data.get('kb_constraints', [])

        # Create CONGENResultData for evaluation
        congen_result = CONGENResultData(
            kb_constraints=kb_constraints,
            redundant_constraints=result_data.get('redundant_constraints', []),
            n_bias=result_data.get('statistics', {}).get('n_bias', 0),
            n_mss=result_data.get('statistics', {}).get('n_mss', 0),
            n_kb=result_data.get('statistics', {}).get('n_kb', len(kb_constraints)),
            bg_clauses=result_data.get('bg_clauses', [])
        )

        # Evaluate
        eval_result = self.evaluator.evaluate(congen_result)
        metrics = eval_result.metrics

        # Count examples
        positive = examples.get('positive', [])
        negative = examples.get('negative', [])

        # Extract sampling strategy from filename
        sampling_strategy = Path(examples_path).stem.split('_')[-1]

        return CONGENMetrics(
            n_examples=len(positive) + len(negative),
            n_positive=len(positive),
            n_negative=len(negative),
            n_kb=len(kb_constraints),
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1_score=metrics.f1_score,
            runtime_ms=result_data.get('metadata', {}).get('runtime_ms', 0.0),
            sampling_strategy=sampling_strategy
        )


def generate_comparison_table(
        comparisons: List[ComparisonResult],
        output_path: Optional[str] = None
) -> str:
    """
    Generate Table 12 style comparison.

    Args:
        comparisons: List of comparison results
        output_path: Optional path to save markdown

    Returns:
        Markdown table string
    """
    # Header
    lines = [
        "| Model | Algorithm | #Queries/Examples | |KB| | Accuracy | Runtime (ms) |",
        "|-------|-----------|-------------------|------|----------|--------------|"
    ]

    for comp in comparisons:
        # CONGEN row
        lines.append(
            f"| {comp.model_name} | CONGEN | {comp.congen.n_examples} | "
            f"{comp.congen.n_kb} | {comp.congen.accuracy:.4f} | "
            f"{comp.congen.runtime_ms:.0f} |"
        )
        # QuAcq row
        lines.append(
            f"| {comp.model_name} | QuAcq | {comp.quacq.n_queries} | "
            f"{comp.quacq.n_kb} | {comp.quacq.accuracy:.4f} | "
            f"{comp.quacq.runtime_ms:.0f} |"
        )

    # Summary
    if comparisons:
        avg_efficiency = sum(c.query_efficiency for c in comparisons) / len(comparisons)
        avg_acc_diff = sum(c.accuracy_diff for c in comparisons) / len(comparisons)

        lines.extend([
            "",
            f"**Average Query Efficiency:** {avg_efficiency:.2f}x",
            f"**Average Accuracy Difference:** {avg_acc_diff:+.4f}"
        ])

    table = "\n".join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(table)

    return table


def save_comparison_json(
        comparisons: List[ComparisonResult],
        output_path: str
) -> None:
    """
    Save comparison results to JSON.

    Args:
        comparisons: List of comparison results
        output_path: Output file path
    """
    data = {
        'comparisons': [c.to_dict() for c in comparisons],
        'summary': {
            'n_models': len(comparisons),
            'avg_query_efficiency': sum(c.query_efficiency for c in comparisons) / len(comparisons) if comparisons else 0,
            'avg_accuracy_diff': sum(c.accuracy_diff for c in comparisons) / len(comparisons) if comparisons else 0
        }
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
