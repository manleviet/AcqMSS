"""
Main evaluator for CONGEN results.

Supports two evaluation strategies:
1. Description-based (recommended): Compare constraint descriptions
2. Clause-based: Compare CNF clauses (semantic)
"""

from dataclasses import dataclass
from typing import List, Set, Tuple
from pathlib import Path
from enum import Enum
import logging

from .oracle_extractor import OracleData
from .bias_loader import BiasData
from .result_loader import CONGENResultData
from .metrics import EvaluationMetrics, compute_metrics


class EvaluationStrategy(Enum):
    """Evaluation strategy."""
    DESCRIPTION = "description"  # Compare constraint descriptions (recommended)
    CLAUSE = "clause"            # Compare CNF clauses (semantic)


@dataclass
class EvaluationResult:
    """
    Complete evaluation result.

    Attributes:
        strategy: Which strategy was used
        metrics: EvaluationMetrics (TP, TN, FP, FN)
        kb_constraints: List of KB constraint IDs
        matched_constraints: TP constraint IDs/descriptions
        missed_constraints: FN - in oracle but not KB
        extra_constraints: FP - in KB but not oracle
        kb_reduction_ratio: 1 - (n_kb / n_bias)
    """
    strategy: str
    metrics: EvaluationMetrics
    kb_constraints: List[str]
    matched_constraints: List[str]
    missed_constraints: List[str]
    extra_constraints: List[str]
    kb_reduction_ratio: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'strategy': self.strategy,
            'metrics': self.metrics.to_dict(),
            'kb_constraints': self.kb_constraints,
            'matched_constraints': self.matched_constraints,
            'missed_constraints': self.missed_constraints,
            'extra_constraints': self.extra_constraints,
            'kb_reduction_ratio': self.kb_reduction_ratio,
        }


class Evaluator:
    """
    Evaluate CONGEN results against Oracle FM.

    Supports two strategies:
    1. Description-based (recommended): Compare constraint descriptions
    2. Clause-based: Compare CNF clauses (semantic)
    """

    def __init__(self, oracle: OracleData, bias: BiasData):
        """
        Initialize evaluator with oracle and bias data.

        Args:
            oracle: OracleData extracted from feature model
            bias: BiasData loaded from bias JSON
        """
        self.oracle = oracle
        self.bias = bias
        logging.debug('Evaluator initialized: oracle=%d descriptions, bias=%d constraints',
                      len(oracle.descriptions), len(bias.constraints))

    def evaluate(
            self,
            result: CONGENResultData,
            strategy: EvaluationStrategy = EvaluationStrategy.DESCRIPTION
    ) -> EvaluationResult:
        """
        Evaluate CONGEN result against Oracle.

        Args:
            result: CONGENResultData with kb_constraints
            strategy: DESCRIPTION (recommended) or CLAUSE

        Returns:
            EvaluationResult with metrics and details
        """
        logging.debug('>>> Evaluator.evaluate(kb=%d, strategy=%s)',
                      len(result.kb_constraints), strategy.value)

        if strategy == EvaluationStrategy.DESCRIPTION:
            return self._evaluate_by_description(result)
        else:
            return self._evaluate_by_clause(result)

    def _evaluate_by_description(self, result: CONGENResultData) -> EvaluationResult:
        """
        Evaluate using description-based strategy.

        1. Get FM descriptions from oracle
        2. Get KB descriptions from bias
        3. Compare string sets
        """
        # Get oracle descriptions (ground truth)
        fm_descriptions = self.oracle.descriptions

        # Get acquired KB descriptions
        acquired_descriptions: Set[str] = set()
        kb_to_description: dict = {}
        for cid in result.kb_constraints:
            if cid.startswith('ne_'):
                continue  # Skip NE constraints
            if cid in self.bias.constraints:
                desc = self.bias.constraints[cid].description
                acquired_descriptions.add(desc)
                kb_to_description[cid] = desc

        # Compute metrics
        tp = acquired_descriptions & fm_descriptions
        fp = acquired_descriptions - fm_descriptions
        fn = fm_descriptions - acquired_descriptions

        metrics = EvaluationMetrics(
            true_positives=len(tp),
            false_positives=len(fp),
            false_negatives=len(fn),
            true_negatives=0  # Not applicable for description-based
        )

        # Find constraint IDs for matched/extra
        matched = [cid for cid, desc in kb_to_description.items() if desc in tp]
        extra = [cid for cid, desc in kb_to_description.items() if desc in fp]
        missed = list(fn)  # Just descriptions (no IDs in FM)

        # KB reduction ratio
        reduction = 1 - (result.n_kb / result.n_bias) if result.n_bias > 0 else 0

        eval_result = EvaluationResult(
            strategy=EvaluationStrategy.DESCRIPTION.value,
            metrics=metrics,
            kb_constraints=result.kb_constraints,
            matched_constraints=matched,
            missed_constraints=missed,
            extra_constraints=extra,
            kb_reduction_ratio=reduction
        )

        logging.debug('<<< Description: P=%.3f, R=%.3f, F1=%.3f',
                      metrics.precision, metrics.recall, metrics.f1_score)

        return eval_result

    def _evaluate_by_clause(self, result: CONGENResultData) -> EvaluationResult:
        """
        Evaluate using clause-based strategy.

        1. Convert KB constraints to CNF clauses (sorted for normalization)
        2. Compare with oracle clause set
        """
        # Convert KB constraint IDs to clause sets (normalized with sorted)
        kb_clauses: Set[Tuple[int, ...]] = set()
        kb_to_clauses: dict = {}
        for cid in result.kb_constraints:
            if cid.startswith('ne_'):
                continue
            if cid in self.bias.constraints:
                constraint_clauses = []
                for clause in self.bias.constraints[cid].clauses:
                    normalized = tuple(sorted(clause))
                    kb_clauses.add(normalized)
                    constraint_clauses.append(normalized)
                kb_to_clauses[cid] = constraint_clauses

        # Get bias clause set
        bias_clauses = self.bias.get_all_clauses()

        # Compute metrics
        metrics = compute_metrics(kb_clauses, self.oracle.clause_set, bias_clauses)

        # Find matched/missed/extra constraints
        matched = self._find_matched_constraints(kb_clauses, kb_to_clauses)
        missed = self._find_missed_clauses_descriptions(kb_clauses)
        extra = self._find_extra_constraints(result.kb_constraints, kb_clauses, kb_to_clauses)

        # KB reduction ratio
        reduction = 1 - (result.n_kb / result.n_bias) if result.n_bias > 0 else 0

        eval_result = EvaluationResult(
            strategy=EvaluationStrategy.CLAUSE.value,
            metrics=metrics,
            kb_constraints=result.kb_constraints,
            matched_constraints=matched,
            missed_constraints=missed,
            extra_constraints=extra,
            kb_reduction_ratio=reduction
        )

        logging.debug('<<< Clause: P=%.3f, R=%.3f, F1=%.3f',
                      metrics.precision, metrics.recall, metrics.f1_score)

        return eval_result

    def _find_matched_constraints(
            self,
            kb_clauses: Set[Tuple[int, ...]],
            kb_to_clauses: dict
    ) -> List[str]:
        """Find constraint IDs that match oracle (clause-based)."""
        matched = []
        for cid, clauses in kb_to_clauses.items():
            for clause in clauses:
                if clause in self.oracle.clause_set:
                    matched.append(cid)
                    break
        return matched

    def _find_missed_clauses_descriptions(
            self,
            kb_clauses: Set[Tuple[int, ...]]
    ) -> List[str]:
        """Find oracle clauses not in KB as string descriptions."""
        missed_clauses = self.oracle.clause_set - kb_clauses
        return [str(list(c)) for c in list(missed_clauses)[:20]]  # Limit to 20

    def _find_extra_constraints(
            self,
            kb_ids: List[str],
            kb_clauses: Set[Tuple[int, ...]],
            kb_to_clauses: dict
    ) -> List[str]:
        """Find KB constraints not in oracle (clause-based)."""
        extra = []
        for cid in kb_ids:
            if cid.startswith('ne_'):
                continue
            if cid in kb_to_clauses:
                clauses = kb_to_clauses[cid]
                if not any(c in self.oracle.clause_set for c in clauses):
                    extra.append(cid)
        return extra

    @classmethod
    def from_files(cls, oracle_path: Path, bias_path: Path) -> 'Evaluator':
        """
        Create Evaluator from file paths.

        Args:
            oracle_path: Path to feature model (.uvl)
            bias_path: Path to bias JSON file

        Returns:
            Evaluator instance
        """
        oracle = OracleData.from_uvl(Path(oracle_path))
        bias = BiasData.from_json(Path(bias_path))
        return cls(oracle, bias)
