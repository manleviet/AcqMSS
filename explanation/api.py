"""Public API façade for the ``explanation`` framework.

This is the single import surface the ``conacq`` application (and any external
consumer) may use. The app depends ONLY on this module plus the top-level
``profiling`` package; it must never reach into ``explanation.models.*``,
``explanation.operations.*`` or ``explanation.transformations.*``, nor import
any underscore-private name. A boundary guard (``tests/test_boundary_guard.py``)
enforces both directions of that contract:

* app → framework only through this façade (no deep paths, no privates);
* framework never imports the app (keeps ``explanation`` reusable in isolation).

The surface is intentionally minimal — it re-exports exactly what the app
consumes today. It grows as later work formalizes further seams (e.g. the
operation registry). Nothing here is re-exported "just in case": add a symbol
only when a consumer needs it.
"""
from explanation.models.task_preparation import (
    Task,
    DiagnosisTask,
    TestCaseTask,
    TaskInput,
    PreparedTask,
    DescriptionProvider,
    TaskPreparationStrategy,
    FrozenDict,
    cf,
    prepare_kb,
    prepare_testsuite_with_negation,
    prepare_variable_assignments,
)
from explanation.models.assumption_id_allocator import AssumptionIdAllocator
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.encoding import (
    config_to_variable_literals,
    variable_literals_to_config,
    config_to_assignment_assumptions,
    get_constraint_vars,
)
from explanation.models.assignment_assumption_map import AssignmentAssumptionMap
from explanation.models.kb_protocol import KBProtocol
from explanation.models.abstract_model_builder import AbstractModelBuilder
from explanation.checker import (
    ConsistencyChecker,
    TestCaseChecker,
    CopyableChecker,
    SolverBackend,
    build_checker,
    SolverTimeoutError,
)
from explanation.operations.algorithms.utils import split, diff, negate_cnf_tseitin
from explanation.operations.algorithms.quickxplain import QuickXPlain
from explanation.operations.registry import (
    register_operation, get_operation, registered_operations,
)
from explanation.transformations.fm_to_diag_pysat import FmToDiagPysat

__all__ = [
    # Task family (frozen pure data) + preparation helpers
    'Task',
    'FrozenDict',
    'DiagnosisTask',
    'TestCaseTask',
    'TaskInput',
    'PreparedTask',
    'DescriptionProvider',
    'TaskPreparationStrategy',
    'cf',
    'AssumptionIdAllocator',
    'prepare_kb',
    'prepare_testsuite_with_negation',
    'prepare_variable_assignments',
    # Test-suite data
    'Assignment',
    'TestCase',
    'TestSuite',
    # Encoding free functions (name↔id catalog owned by the KB, passed in)
    'config_to_variable_literals',
    'variable_literals_to_config',
    'config_to_assignment_assumptions',
    'get_constraint_vars',
    'AssignmentAssumptionMap',
    # KB structural contract
    'KBProtocol',
    # Model-builder base (conacq's OracleBiasModelBuilder inherits this)
    'AbstractModelBuilder',
    # Consistency-checker port (Protocols) + the single construction door
    'ConsistencyChecker',
    'TestCaseChecker',
    'CopyableChecker',
    'SolverBackend',
    'build_checker',
    'SolverTimeoutError',
    # Clause utilities
    'split',
    'diff',
    'negate_cnf_tseitin',
    'QuickXPlain',
    # Operation registry (the plugin seam)
    'register_operation',
    'get_operation',
    'registered_operations',
    # Transformation entry point
    'FmToDiagPysat',
]
