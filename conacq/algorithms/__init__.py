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

# Passive learning (ConGen) - expose from acqmss subpackage
from .acqmss import (
    AcqMSS,
    Reduce,
    GenerateNE,
    ConGen,
    ConGenResult,
    ConGenModel,
    ConGenModelBuilder,
)

# Interactive learning (QuAcq)
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
    'ConGen',
    'ConGenResult',
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
