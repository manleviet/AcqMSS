"""
Constraint Acquisition Algorithms.

This package provides implementations of constraint acquisition algorithms:

CONGEN (Passive/Batch Learning):
- ACQMSS: Divide-and-conquer algorithm for finding MSS of bias
- REDUCE: Redundancy elimination from acquired KB
- GenerateNE: Negated negative examples generation using QuickXPlain
- CONGEN: Main constraint acquisition algorithm

Interactive Learning (QuAcq):
- QuAcq: Interactive constraint acquisition via membership queries
- QueryGenerator: SAT-based query generation
- InteractiveLearner: High-level interface for interactive learning

Task classes for both incremental and non-incremental modes.
"""

from .acqmss import ACQMSS
from .reduce import Reduce
from .generate_ne import GenerateNE, NEResult
from .congen import CONGEN, CONGENResult
from .task import CONGENTask, IncrementalCONGENTask, NonIncrementalCONGENTask
from .task_preparation import (
    IncrementalCONGENTaskPreparation,
    NonIncrementalCONGENTaskPreparation
)
from .model import CONGENModel

# Interactive learning components
from .interactive import (
    InteractiveLearner,
    QuAcq,
    QueryGenerator,
    InteractiveTask,
    InteractiveResult,
    AutomatedOracle,
    UserPromptOracle,
    CachedOracle,
    run_interactive_learning
)

# Re-export explanation module classes for convenience
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.task_preparation import TaskInput

__all__ = [
    # CONGEN (passive learning)
    'ACQMSS',
    'Reduce',
    'GenerateNE',
    'NEResult',
    'CONGEN',
    'CONGENResult',
    'CONGENTask',
    'IncrementalCONGENTask',
    'NonIncrementalCONGENTask',
    'IncrementalCONGENTaskPreparation',
    'NonIncrementalCONGENTaskPreparation',
    'CONGENModel',
    # Interactive learning (QuAcq)
    'InteractiveLearner',
    'QuAcq',
    'QueryGenerator',
    'InteractiveTask',
    'InteractiveResult',
    'AutomatedOracle',
    'UserPromptOracle',
    'CachedOracle',
    'run_interactive_learning',
    # Re-exports from explanation module
    'Assignment',
    'TestCase',
    'TestSuite',
    'TaskInput',
]
