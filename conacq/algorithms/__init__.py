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
- QueryProvider: Unified query provider (pool + SAT)

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
from .quacq import (
    QuAcq,
    QuAcqModel,
    QuAcqModelBuilder,
    QuAcqTask,
    QuAcqResult,
    FeatureModelOracle,
    UserPromptOracle,
    CachedOracle,
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
    'QuAcq',
    'QuAcqModel',
    'QuAcqModelBuilder',
    'QuAcqTask',
    'QuAcqResult',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    # Re-exports from explanation module
    'Assignment',
    'TestCase',
    'TestSuite',
    'TaskInput',
]
