"""
A Java version of this implementation is available at:
https://github.com/HiConfiT/hiconfit-core/tree/main/ca-cdr-package/src/main/java/at/tugraz/ist/ase/cacdr/algorithms/hs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Any, Sequence

from explanation.checker.protocols import ConsistencyChecker


class LabelerType(Enum):
    CONFLICT = 1
    DIAGNOSIS = 2


@dataclass
class AbstractHSParameters:
    set_c: Sequence[int]


class IHSLabelable(ABC):
    """
    Interface for the HSDAG's labeler
    """

    # Root HSDAG-node parameters. Concrete labelers set this in their __init__; the
    # getter below reads it. Declared here (not set in a base __init__) so the getter's
    # contract is visible without injecting an __init__ into the labelers' multiple-
    # inheritance MRO (each is ``<Algorithm>, IHSLabelable``).
    initial_parameters: AbstractHSParameters

    @abstractmethod
    def get_type(self) -> LabelerType:
        pass

    def get_initial_parameters(self) -> AbstractHSParameters:
        """Return the root node's parameters (set by the concrete labeler's __init__).

        Pulled up from the four concrete labelers — all were the identical
        ``return self.initial_parameters``.
        """
        return self.initial_parameters

    @abstractmethod
    def get_label(self, parameters: AbstractHSParameters) -> List[List]:
        pass

    @abstractmethod
    def identify_new_node_parameters(self, param_parent_node: AbstractHSParameters,
                                     arc_label: Any) -> AbstractHSParameters:
        pass

    @abstractmethod
    def get_instance(self, checker: ConsistencyChecker) -> 'IHSLabelable':
        pass
