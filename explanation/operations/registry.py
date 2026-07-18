"""Operation registry — a name → operation-class seam (the plugin door).

Additive: no production code depends on this yet. It lets a caller look up a PySAT
operation class by a stable key instead of importing the concrete class, which is the
seam a future plugin or config-driven dispatch would register into. The built-in
operations register themselves at import (see ``_register_builtins``).

All registered classes are ``PySATAbstractExplanation`` subclasses — including the redundancy
operations, which are now first-class (their ``execute()`` is real), not a diagnosis
op with the HSDAG stubbed out.
"""
from typing import Dict, Type

from explanation.operations.pysat_abstract_explanation import PySATAbstractExplanation


_REGISTRY: Dict[str, Type[PySATAbstractExplanation]] = {}


def register_operation(name: str, operation_cls: Type[PySATAbstractExplanation]) -> None:
    """Register *operation_cls* under a stable *name* (overwrites an existing entry)."""
    _REGISTRY[name] = operation_cls


def get_operation(name: str) -> Type[PySATAbstractExplanation]:
    """Return the operation class registered under *name* (``KeyError`` if absent)."""
    return _REGISTRY[name]


def registered_operations() -> Dict[str, Type[PySATAbstractExplanation]]:
    """Return a copy of the current name → class registry."""
    return dict(_REGISTRY)


def _register_builtins() -> None:
    """Register the built-in PySAT operations. Imports are local so registry.py can be
    imported without eagerly pulling every operation module at definition time."""
    from explanation.operations.pysat_diagnosis import PySATDiagnosis
    from explanation.operations.pysat_conflict import PySATConflict
    from explanation.operations.pysat_testcase import PySATTestCase
    from explanation.operations.pysat_testcase_quickxplain import PySATTestCaseQuickXPlain
    from explanation.operations.pysat_redundancy_constraints import PySATRedundancyConstraints
    from explanation.operations.pysat_redundancy_testcases import PySATRedundancyTestCases

    for name, operation_cls in (
        ("diagnosis", PySATDiagnosis),
        ("conflict", PySATConflict),
        ("testcase", PySATTestCase),
        ("testcase_quickxplain", PySATTestCaseQuickXPlain),
        ("redundancy_constraints", PySATRedundancyConstraints),
        ("redundancy_testcases", PySATRedundancyTestCases),
    ):
        register_operation(name, operation_cls)


_register_builtins()
