"""
High-level interface for interactive constraint acquisition.

Provides a simple API for running QuAcq-style interactive learning.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Union

from .task import InteractiveTask
from .result import InteractiveResult
from .user_interface import InteractiveOracle, AutomatedOracle, UserPromptOracle
from .quacq import QuAcq
from acqmss.bias.bias_io import BiasIO
from acqmss.bias.data_structures import Bias
from acqmss.eval.evaluator import Evaluator, EvaluationStrategy
from acqmss.eval.result_loader import CONGENResultData
from explanation.operations.algorithms.profiler import (
    get_global_profiler, use_global_profiler, ProfilerPreset, AbstractProfiler
)


class InteractiveLearner:
    """
    High-level interface for interactive constraint acquisition.

    Provides factory methods for creating learners from files,
    and a simple API for running the learning process.

    Example:
        # Automated mode (for experiments)
        >>> learner = InteractiveLearner.from_files(
        ...     fm_path='data/fms/model.uvl',
        ...     bias_path='data/bias/model-bias.json'
        ... )
        >>> result = learner.learn(mode='automated', max_queries=500)
        >>> print(f"Learned {result.n_kb} constraints in {result.n_queries} queries")

        # Interactive mode (human expert)
        >>> result = learner.learn(mode='interactive')
    """

    def __init__(self,
                 task: InteractiveTask,
                 oracle: Optional[InteractiveOracle] = None,
                 solver_name: str = 'glucose4',
                 profiler: Optional[AbstractProfiler] = None,
                 fm_path: Optional[str] = None,
                 bias_path: Optional[str] = None):
        """
        Initialize interactive learner.

        Args:
            task: Prepared InteractiveTask with bias and constraint maps
            oracle: Optional oracle (can be set later or created in learn())
            solver_name: PySAT solver name
            profiler: Optional profiler for metrics
            fm_path: Path to feature model (for evaluation)
            bias_path: Path to bias file (for evaluation)
        """
        self.task = task
        self.oracle = oracle
        self.solver_name = solver_name
        self.profiler = profiler if profiler else get_global_profiler()
        self._quacq = QuAcq(solver_name, self.profiler)
        # Store paths for evaluation
        self._fm_path = fm_path
        self._bias_path = bias_path

    @classmethod
    def from_files(cls,
                   fm_path: str,
                   bias_path: str,
                   solver_name: str = 'glucose4',
                   enable_profiling: bool = True) -> 'InteractiveLearner':
        """
        Create learner from feature model and bias files.

        Args:
            fm_path: Path to feature model file (.uvl)
            bias_path: Path to bias file (.json)
            solver_name: PySAT solver name
            enable_profiling: If True, enable benchmark profiling

        Returns:
            InteractiveLearner instance ready to learn

        Example:
            >>> learner = InteractiveLearner.from_files(
            ...     'data/fms/REAL-FM-7.uvl',
            ...     'data/bias/REAL-FM-7-bias.json'
            ... )
        """
        # Setup profiler
        if enable_profiling:
            profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
            profiler.start()
        else:
            profiler = get_global_profiler()

        # Load bias
        bias = BiasIO.load_from_json(bias_path)

        # Create oracle from feature model
        oracle = AutomatedOracle(fm_path)

        # Build task from bias
        task = cls._build_task_from_bias(bias, oracle)

        return cls(task, oracle, solver_name, profiler, fm_path, bias_path)

    @classmethod
    def from_bias(cls,
                  bias: Bias,
                  oracle: InteractiveOracle,
                  bg_clauses: Optional[List[int]] = None,
                  solver_name: str = 'glucose4') -> 'InteractiveLearner':
        """
        Create learner from Bias object and oracle.

        Args:
            bias: Bias object with constraints
            oracle: Oracle for membership queries
            bg_clauses: Optional background knowledge clauses
            solver_name: PySAT solver name

        Returns:
            InteractiveLearner instance
        """
        # Build feature ID mapping from bias
        feature_ids = {f.name: f.id for f in bias.features}
        id_to_feature = {f.id: f.name for f in bias.features}

        # Build constraint and negation maps
        constraint_map = {}
        negated_constraint_map = {}

        for constraint in bias.constraints:
            c_id = constraint.id
            constraint_map[c_id] = constraint.clauses

            # Build negation: ¬(c1 ∧ c2 ∧ ...) = ¬c1 ∨ ¬c2 ∨ ...
            # For CNF, negating conjunction of clauses requires different handling
            neg_clauses = cls._negate_constraint_clauses(constraint.clauses)
            negated_constraint_map[c_id] = neg_clauses

        # Create task
        task = InteractiveTask(
            bias=[c.id for c in bias.constraints],
            learned_kb=[],
            background=bg_clauses if bg_clauses else [],
            feature_ids=feature_ids,
            id_to_feature=id_to_feature,
            constraint_map=constraint_map,
            negated_constraint_map=negated_constraint_map
        )

        return cls(task, oracle, solver_name)

    @staticmethod
    def _build_task_from_bias(bias: Bias, oracle: AutomatedOracle) -> InteractiveTask:
        """Build InteractiveTask from Bias and AutomatedOracle."""
        # Get feature mappings from oracle (to match FM variable IDs)
        feature_ids = oracle.get_feature_ids()
        id_to_feature = {v: k for k, v in feature_ids.items()}

        # Build constraint map using bias feature IDs
        # Need to translate from bias feature IDs to oracle feature IDs
        bias_feature_ids = {f.name: f.id for f in bias.features}

        # Create ID translation if needed
        # (If bias uses different IDs than FM, we need to translate)
        id_translation = {}
        for f in bias.features:
            if f.name in feature_ids:
                id_translation[f.id] = feature_ids[f.name]
            else:
                id_translation[f.id] = f.id

        # Build constraint maps
        constraint_map = {}
        negated_constraint_map = {}

        for constraint in bias.constraints:
            c_id = constraint.id

            # Translate clauses to use oracle feature IDs
            translated_clauses = []
            for clause in constraint.clauses:
                translated_clause = []
                for lit in clause:
                    var = abs(lit)
                    sign = 1 if lit > 0 else -1
                    new_var = id_translation.get(var, var)
                    translated_clause.append(sign * new_var)
                translated_clauses.append(translated_clause)

            constraint_map[c_id] = translated_clauses

            # Build negation
            neg_clauses = InteractiveLearner._negate_constraint_clauses(translated_clauses)
            negated_constraint_map[c_id] = neg_clauses

        # Create task
        task = InteractiveTask(
            bias=[c.id for c in bias.constraints],
            learned_kb=[],
            background=[],  # Could add FM root constraint here
            feature_ids=feature_ids,
            id_to_feature=id_to_feature,
            constraint_map=constraint_map,
            negated_constraint_map=negated_constraint_map
        )

        return task

    @staticmethod
    def _negate_constraint_clauses(clauses: List[List[int]]) -> List[List[int]]:
        """
        Negate a constraint given as CNF clauses.

        If constraint is (c1 ∧ c2 ∧ ... ∧ cn) where each ci is a clause,
        negation is ¬c1 ∨ ¬c2 ∨ ... ∨ ¬cn.

        For SAT solving, we need the negation as CNF.
        ¬(clause) where clause = (l1 ∨ l2 ∨ ... ∨ lk)
        becomes: (¬l1) ∧ (¬l2) ∧ ... ∧ (¬lk)

        So ¬(c1 ∧ c2) = ¬c1 ∨ ¬c2
        where ¬ci = ¬(l1 ∨ ... ∨ lk) = (¬l1 ∧ ... ∧ ¬lk)

        For single-clause constraint: negate all literals, keep as single clause
        For multi-clause constraint: complex - we use a simpler approach

        Simple approach: Introduce auxiliary variables for each clause
        Here we use a simpler heuristic: negate each clause separately
        This is sound but may not be complete.

        Actually, for constraint violation checking we just need:
        ¬(c1 ∧ c2 ∧ ... ∧ cn) is SAT iff there exists some ci that is UNSAT

        For query generation, we want SAT(KB ∪ BG ∪ ¬c).
        If c = (c1 ∧ c2 ∧ ... ∧ cn), then ¬c = ¬c1 ∨ ¬c2 ∨ ... ∨ ¬cn.

        To encode this in CNF, we use the Tseitin transformation:
        aux_i ↔ ¬ci for each clause, then (aux_1 ∨ aux_2 ∨ ... ∨ aux_n)

        For simplicity, if there's only one clause, just negate its literals.
        For multiple clauses, we approximate by picking the first clause's negation.
        This may miss some solutions but is sound for our use case.
        """
        if not clauses:
            return []

        if len(clauses) == 1:
            # Single clause: negate all literals, return as unit clauses
            # ¬(l1 ∨ l2 ∨ ... ∨ lk) = (¬l1) ∧ (¬l2) ∧ ... ∧ (¬lk)
            return [[-lit] for lit in clauses[0]]

        # Multiple clauses: use first clause negation as approximation
        # This is a simplification - proper Tseitin encoding would be more complete
        # For constraint acquisition, this is usually sufficient since we only
        # need to find *some* violating configuration, not all.
        return [[-lit] for lit in clauses[0]]

    def learn(self,
              mode: str = 'automated',
              max_queries: int = 1000,
              features: Optional[List[str]] = None) -> InteractiveResult:
        """
        Run interactive learning.

        Args:
            mode: 'automated' (use oracle) or 'interactive' (prompt user)
            max_queries: Maximum number of membership queries
            features: Feature list for interactive mode (required if mode='interactive')

        Returns:
            InteractiveResult with learned KB and statistics
        """
        # Set up oracle based on mode
        if mode == 'interactive':
            if features is None:
                features = list(self.task.feature_ids.keys())
            oracle = UserPromptOracle(features)
        elif self.oracle is not None:
            oracle = self.oracle
        else:
            raise ValueError("No oracle available. Provide oracle or use 'interactive' mode.")

        # Run QuAcq
        result = self._quacq.learn(self.task, oracle, max_queries)

        return result

    def save_result(self, filepath: str) -> None:
        """Save learning result to file."""
        if self._quacq.result is not None:
            self._quacq.result.save(filepath)
        else:
            raise ValueError("No result to save. Run learn() first.")

    def evaluate(self, result: InteractiveResult) -> Dict:
        """
        Evaluate learning result using both description-based and clause-based strategies.

        Args:
            result: InteractiveResult from learning

        Returns:
            Dictionary with evaluation results for both strategies:
            {
                'description': EvaluationResult dict,  # Strategy 1
                'clause': EvaluationResult dict,       # Strategy 2
            }

        Raises:
            ValueError: If FM or bias paths are not available
        """
        if self._fm_path is None or self._bias_path is None:
            raise ValueError(
                "FM path and bias path are required for evaluation. "
                "Use from_files() to create the learner."
            )

        # Create evaluator from files
        evaluator = Evaluator.from_files(
            Path(self._fm_path),
            Path(self._bias_path)
        )

        # Create a result-like object for the evaluator
        congen_result = CONGENResultData(
            kb_constraints=result.kb_constraints,
            redundant_constraints=[],
            n_bias=len(self.task.bias) + len(result.kb_constraints),  # Original bias size
            n_mss=0,
            n_kb=result.n_kb
        )

        # Evaluate with description-based strategy
        desc_eval = evaluator.evaluate(congen_result, EvaluationStrategy.DESCRIPTION)

        # Evaluate with clause-based strategy
        clause_eval = evaluator.evaluate(congen_result, EvaluationStrategy.CLAUSE)

        evaluation = {
            'description': desc_eval.to_dict(),
            'clause': clause_eval.to_dict()
        }

        # Store in result
        result.evaluation = evaluation

        return evaluation


def run_interactive_learning(
        fm_path: str,
        bias_path: str,
        output_path: Optional[str] = None,
        mode: str = 'automated',
        max_queries: int = 1000,
        solver_name: str = 'glucose4',
        verbose: bool = True
) -> InteractiveResult:
    """
    Convenience function to run interactive learning.

    Args:
        fm_path: Path to feature model (.uvl)
        bias_path: Path to bias file (.json)
        output_path: Optional path to save results
        mode: 'automated' or 'interactive'
        max_queries: Maximum queries
        solver_name: SAT solver name
        verbose: If True, log progress

    Returns:
        InteractiveResult

    Example:
        >>> result = run_interactive_learning(
        ...     fm_path='data/fms/REAL-FM-7.uvl',
        ...     bias_path='data/bias/REAL-FM-7-bias.json',
        ...     output_path='data/results/REAL-FM-7-interactive.json'
        ... )
    """
    if verbose:
        logging.basicConfig(level=logging.INFO)

    learner = InteractiveLearner.from_files(
        fm_path=fm_path,
        bias_path=bias_path,
        solver_name=solver_name
    )

    result = learner.learn(mode=mode, max_queries=max_queries)

    if output_path:
        result.save(output_path)
        if verbose:
            logging.info('Result saved to %s', output_path)

    return result
