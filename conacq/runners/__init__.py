"""
Execution runners for constraint acquisition algorithms.

BaseRunner: ABC defining build-once/run-many/cleanup-once lifecycle.
BaseRunResult: Shared result dataclass (9 fields common to both runners).
ConGenRunner: Run ConGen (passive learning) with performance metrics.
ConMinRunner: Run ConMin (passive maximally-general acquisition) with metrics.
QuAcqRunner: Run QuAcq (interactive learning) with performance metrics.
"""

from .base_runner import BaseRunner, BaseRunResult
from .congen_runner import ConGenRunner, ConGenRunResult
from .conmin_runner import ConMinRunner, ConMinRunResult
from .quacq_runner import QuAcqRunner, QuAcqRunResult

__all__ = [
    'BaseRunner', 'BaseRunResult',
    'ConGenRunner', 'ConGenRunResult',
    'ConMinRunner', 'ConMinRunResult',
    'QuAcqRunner', 'QuAcqRunResult',
]
