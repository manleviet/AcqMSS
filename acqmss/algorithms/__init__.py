"""
CONGEN Constraint Acquisition Algorithms.

This package provides implementations of the CONGEN algorithm and its sub-algorithms:
- ACQMSS: Divide-and-conquer algorithm for finding MSS of bias
- REDUCE: Redundancy elimination from acquired KB
- GenerateNE: Negated negative examples generation using QuickXPlain
- CONGEN: Main constraint acquisition algorithm

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

# Re-export explanation module classes for convenience
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.task_preparation import TaskInput

__all__ = [
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
    # Re-exports from explanation module
    'Assignment',
    'TestCase',
    'TestSuite',
    'TaskInput',
]
