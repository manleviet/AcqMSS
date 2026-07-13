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
- FMOracle: FM-based oracle for automated experiments
- UserPromptOracle: Prompts human expert for interactive mode
- CachedOracle: Wrapper that caches oracle answers

Example Usage:
    from conacq.algorithms.quacq import QuAcqModelBuilder, QuAcq, DiscriminatingGenerator
    from conacq.example_generators import QueryProvider

    model = (QuAcqModelBuilder
             .from_bias('data/bias/model-bias.json')
             .with_oracle(oracle)
             .build())
    task = model.task
    checker = build_checker(task, SolverBackend.from_flags(use_incremental=model.use_incremental))
    query_provider = QueryProvider()
    profiler = get_global_profiler()
    discrim_gen = DiscriminatingGenerator(
        checker=checker, model=model, profiler=profiler, root_assumption=task.set_b[0])
    quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen, model=model)
    result = quacq.learn(
        set_c=task.set_c, set_b=task.set_b,
        negation_map=task.negation_map, mode='oracle')
"""

from .task_preparation import QuAcqTask, QuAcqTaskPreparation
from .quacq_model import QuAcqModel
from .quacq_model_builder import QuAcqModelBuilder
from conacq.oracle import (
    Oracle,
    FMOracle,
    UserPromptOracle,
    CachedOracle,
)
from .quacq import QuAcq, QuAcqResult
from .findscope import FindScope
from .findc import FindC
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
    'FMOracle',
    'UserPromptOracle',
    'CachedOracle',
    # FindScope/FindC
    'FindScope',
    'FindC',
    # DiscriminatingGenerator
    'DiscriminatingGenerator',
]
