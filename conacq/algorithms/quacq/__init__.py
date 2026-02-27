"""
QuAcq constraint acquisition package.

This package implements the QuAcq algorithm for interactive constraint acquisition,
where an oracle (automated or human) answers membership queries to guide learning.

Main Components:
- QuAcq: Core algorithm implementation
- QuAcqModel: Model building and preparation (assumption-ID based)
- QuAcqTask: Assumption-ID-based task state
- QuAcqTaskPreparation: Task preparation (co-located in quacq_task.py)
- QuAcqResult: Learning result data structure (co-located in quacq.py)

Oracle Implementations:
- FeatureModelOracle: FM-based oracle for automated experiments
- UserPromptOracle: Prompts human expert for interactive mode
- CachedOracle: Wrapper that caches oracle answers

Example Usage:
    from conacq.algorithms.quacq import QuAcqModelBuilder, QuAcq

    model = (QuAcqModelBuilder
             .from_bias('data/bias/model-bias.json')
             .with_oracle(oracle)
             .build())
    task = model.task
    result = QuAcq().learn(task, oracle, model.description_provider)
"""

from .task_preparation import QuAcqTask, QuAcqTaskPreparation
from .quacq_model import QuAcqModel
from .quacq_model_builder import QuAcqModelBuilder
from conacq.oracle import (
    Oracle,
    FeatureModelOracle,
    UserPromptOracle,
    CachedOracle,
)
from .quacq import QuAcq, QuAcqResult
from .findscope import find_scope
from .findc import find_c
from .discriminating_generator import DiscriminatingGenerator

__all__ = [
    # Core algorithm
    'QuAcq',
    # Task types
    'QuAcqTask',
    # Result types
    'QuAcqResult',
    # Model, builder, and preparation
    'QuAcqModel',
    'QuAcqModelBuilder',
    'QuAcqTaskPreparation',
    # Oracle implementations
    'Oracle',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    # FindScope/FindC
    'find_scope',
    'find_c',
    # DiscriminatingGenerator
    'DiscriminatingGenerator',
]
