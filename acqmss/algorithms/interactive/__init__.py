"""
Interactive (QuAcq-style) constraint acquisition module.

This module implements interactive learning for constraint acquisition,
where an oracle (automated or human) answers membership queries to guide
the learning process.

Main Components:
- InteractiveLearner: High-level interface for interactive learning
- QuAcq: Core QuAcq algorithm implementation
- QueryGenerator: SAT-based query generation
- InteractiveTask: Task state management
- InteractiveResult: Learning result data structure

Oracle Implementations:
- AutomatedOracle: Uses FeatureModelOracle for automated experiments
- UserPromptOracle: Prompts human expert for interactive mode
- CachedOracle: Wrapper that caches oracle answers

Example Usage:
    # Automated mode (for experiments)
    from acqmss.algorithms.interactive import InteractiveLearner

    learner = InteractiveLearner.from_files(
        fm_path='data/fms/model.uvl',
        bias_path='data/bias/model-bias.json'
    )
    result = learner.learn(mode='automated', max_queries=500)
    print(f"Learned {result.n_kb} constraints in {result.n_queries} queries")

    # Interactive mode (human expert)
    result = learner.learn(mode='interactive')

    # Convenience function
    from acqmss.algorithms.interactive import run_interactive_learning

    result = run_interactive_learning(
        fm_path='data/fms/model.uvl',
        bias_path='data/bias/model-bias.json',
        output_path='results/model-interactive.json'
    )
"""

from .task import InteractiveTask
from .result import InteractiveResult
from acqmss.oracle import (
    InteractiveOracle,
    AutomatedOracle,
    UserPromptOracle,
    CachedOracle,
    ExampleProvider,
)
from .query_generator import QueryGenerator
from .quacq import QuAcq
from .findscope import find_scope
from .findc import find_c
from .learner import InteractiveLearner, run_interactive_learning

__all__ = [
    # Core classes
    'InteractiveLearner',
    'QuAcq',
    'QueryGenerator',
    'InteractiveTask',
    'InteractiveResult',
    # Oracle implementations
    'InteractiveOracle',
    'AutomatedOracle',
    'UserPromptOracle',
    'CachedOracle',
    'ExampleProvider',
    # FindScope/FindC
    'find_scope',
    'find_c',
    # Convenience function
    'run_interactive_learning',
]
