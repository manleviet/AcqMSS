"""
Constraint Acquisition Algorithms.

This package provides implementations of constraint acquisition algorithms:

ConGen (Passive/Batch Learning):
- AcqMSS: Divide-and-conquer algorithm for finding MSS of bias
- REDUCE: Redundancy elimination from acquired KB
- GenerateNE: Negated negative examples generation using QuickXPlain
- ConGen: Main constraint acquisition algorithm

Interactive Learning (QuAcq):
- QuAcq: Interactive constraint acquisition via membership queries
- QueryGenerator: SAT-based query generation
- InteractiveLearner: High-level interface for interactive learning

Task classes shared across incremental and non-incremental modes.
"""

from .acqmss import AcqMSS
from .reduce import Reduce
from .generate_ne import GenerateNE, NEPerTestcase
from .congen import ConGen, CONGENResult, resolve_congen_names
from .task_preparation import ConGenTask
from .task_preparation import ConGenTaskPreparation
from .congen_model import ConGenModel
from .congen_model_builder import ConGenModelBuilder

# Interactive learning components
from .interactive import (
    InteractiveLearner,
    QuAcq,
    InteractiveTask,
    InteractiveResult,
    FeatureModelOracle,
    UserPromptOracle,
    CachedOracle,
    run_interactive_learning
)

# Re-export explanation module classes for convenience
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.task_preparation import TaskInput

__all__ = [
    # ConGen (passive learning)
    'AcqMSS',
    'Reduce',
    'GenerateNE',
    'NEPerTestcase',
    'ConGen',
    'CONGENResult',
    'resolve_congen_names',
    'ConGenTask',
    'ConGenTaskPreparation',
    'ConGenModel',
    'ConGenModelBuilder',
    # Interactive learning (QuAcq)
    'InteractiveLearner',
    'QuAcq',
    'InteractiveTask',
    'InteractiveResult',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    'run_interactive_learning',
    # Re-exports from explanation module
    'Assignment',
    'TestCase',
    'TestSuite',
    'TaskInput',
]
