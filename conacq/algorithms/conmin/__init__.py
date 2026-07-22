"""ConMin: passive maximally-general constraint acquisition (AAAI).

P1 exposes the Stage-1 scaffold — ``ConMin.acquire`` runs paper Algorithm 1 lines
1-4 (consistency gate + AcqMSS), returning the maximally-specific admissible pool A.
The cover (AcqMinCover), support, and Reduce steps land in P2-P3.

Reuses AcqMSS / GenerateNE / Reduce from the sibling ``acqmss`` package by import
(no fork); the min-cover engine (P2) will be in-repo.
"""

from .conmin import ConMin, ConMinResult
from .conmin_model import ConMinModel
from .conmin_model_builder import ConMinModelBuilder
from .task_preparation import (
    ConMinTask,
    ConMinTaskInput,
    ConMinTaskPreparation,
)
from .acqmincover import AcqMinCover, CoverResult, NegEncoding
from .support import support, build_support_count

__all__ = [
    'ConMin',
    'ConMinResult',
    'ConMinModel',
    'ConMinModelBuilder',
    'ConMinTask',
    'ConMinTaskInput',
    'ConMinTaskPreparation',
    # P2 — cover engine
    'AcqMinCover',
    'CoverResult',
    'NegEncoding',
    # P3 — support⁺
    'support',
    'build_support_count',
]
