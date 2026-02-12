"""
High-level interface for interactive constraint acquisition.

Provides a simple API for running QuAcq-style interactive learning.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Union

from .task import InteractiveTask
from .result import InteractiveResult
from .user_interface import InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider
from .quacq import QuAcq
from acqmss.bias.bias_io import BiasIO
from acqmss.bias.data_structures import Bias
from acqmss.eval.evaluator import Evaluator, EvaluationStrategy
from acqmss.eval.result_loader import CONGENResultData
from explanation.operations.algorithms.utils import negate_cnf_tseitin
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

        # Compute tseitin_start from max feature variable ID
        tseitin_var = max(f.id for f in bias.features) + 1

        for constraint in bias.constraints:
            c_id = constraint.id
            constraint_map[c_id] = constraint.clauses

            # Proper Tseitin negation for all constraints (single and multi-clause)
            neg_clauses, tseitin_var = negate_cnf_tseitin(constraint.clauses, tseitin_var)
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

        # Compute tseitin_start from max variable ID across both spaces
        max_var = max(max(feature_ids.values()), max(f.id for f in bias.features))
        tseitin_var = max_var + 1

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

            # Proper Tseitin negation
            neg_clauses, tseitin_var = negate_cnf_tseitin(translated_clauses, tseitin_var)
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

    @classmethod
    def from_examples(cls,
                      fm_path: str,
                      bias_path: str,
                      examples: List[Dict[str, bool]],
                      seed: int = None,
                      solver_name: str = 'glucose4',
                      enable_profiling: bool = True) -> 'InteractiveLearner':
        """
        Create learner for example-based mode.

        Args:
            fm_path: Path to feature model file (.uvl)
            bias_path: Path to bias file (.json)
            examples: Mixed list of examples (no E+/E- distinction)
            seed: Random seed for example shuffling
            solver_name: PySAT solver name
            enable_profiling: If True, enable benchmark profiling

        Returns:
            InteractiveLearner configured for example-based learning
        """
        if enable_profiling:
            profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
            profiler.start()
        else:
            profiler = get_global_profiler()

        bias = BiasIO.load_from_json(bias_path)
        oracle = AutomatedOracle(fm_path)
        task = cls._build_task_from_bias(bias, oracle)

        learner = cls(task, oracle, solver_name, profiler, fm_path, bias_path)
        learner._example_provider = ExampleProvider(examples, seed)
        learner._fm_clauses = oracle.fm_oracle.cnf_clauses
        return learner

    def learn_from_examples(self,
                            query_mode: str = 'example_only',
                            max_queries: int = 10000) -> InteractiveResult:
        """
        Run example-based learning (ExampleProvider + ConsistencyChecker).

        Args:
            query_mode: 'example_only' or 'example_first'
            max_queries: Maximum queries before stopping

        Returns:
            InteractiveResult with learned KB

        Raises:
            ValueError: If learner not created with from_examples()
        """
        if not hasattr(self, '_example_provider') or not hasattr(self, '_fm_clauses'):
            raise ValueError("Use from_examples() to create learner for example-based mode")

        result = self._quacq.learn_from_examples(
            self.task, self._example_provider, self._fm_clauses,
            query_mode=query_mode, max_queries=max_queries
        )
        return result

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
