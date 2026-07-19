"""Guard: the parallel-HSDAG scaffolding is kept on purpose, not dead code.

See docs/adr/0014-parallel-executor-deferred-to-canonical.md — the parallel
executor is deferred to the canonical repo, but the seams that make re-enabling
it drop-in (the ``get_instance`` clone hook on the labeler contract and the
``MULTI_PROCESS`` profiler mode) stay in AcqMSS. This test pins the MECHANISM of
those seams so a future "0-caller → delete" sweep trips here instead of quietly
removing them.
"""
from explanation.operations.algorithms.hsdag.labeler.labeler import IHSLabelable
from explanation.operations.algorithms.hsdag.labeler.fastdiag_labeler import (
    FastDiagLabeler,
)
from explanation.operations.algorithms.hsdag.labeler.kbdiag_labeler import (
    KBDiagLabeler,
)
from explanation.operations.algorithms.hsdag.labeler.quickxplain_labeler import (
    QuickXPlainLabeler,
)
from explanation.operations.algorithms.hsdag.labeler.quickxplain_with_testcases_labeler import (
    QuickXPlainWithTestCasesLabeler,
)
from profiling import ProfilerMode


def test_parallel_scaffolding_is_intentional():
    # Guards the deferred-executor seams per ADR-0014. Assert the mechanism
    # (ABC enforcement, real overrides, enum member), never a docstring/marker.

    # 1. get_instance is abstract on the base contract — the ABC machinery
    #    itself blocks instantiation without an override.
    assert "get_instance" in IHSLabelable.__abstractmethods__

    # 2. Each concrete labeler genuinely overrides it (own __dict__, not merely
    #    inherited) — this is the per-worker clone hook the parallel executor uses.
    for cls in (
        FastDiagLabeler,
        KBDiagLabeler,
        QuickXPlainLabeler,
        QuickXPlainWithTestCasesLabeler,
    ):
        assert "get_instance" in cls.__dict__, (
            f"{cls.__name__} must override get_instance (parallel clone hook)"
        )

    # 3. The multiprocess profiler mode survives for parallel workers.
    assert hasattr(ProfilerMode, "MULTI_PROCESS")
