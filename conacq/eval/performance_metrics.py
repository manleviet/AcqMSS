"""
Performance metrics collection for ConGen and QuAcq evaluation.

Core metrics (Table 7-8 in the paper):
- #consistency_checks: Number of SAT solver calls
- runtime_ms: Execution time (ms)
- memory_peak_mb: Peak memory usage (MB)
- n_mss: MSS size before REDUCE
- n_kb: Final KB size

ConGen extended metrics from profiler:
- congen_runtime_ms, acqmss_runtime_ms, acqmss_calls
- reduce_runtime_ms, solver_time_ms
- is_consistent_calls, is_consistent_test_cases_calls
- redundancy_consistency_checks

QuAcq-specific metrics:
- quacq_runtime_ms, query_generation_runtime_ms, findscope_runtime_ms
- findc_runtime_ms, dis_gen_runtime_ms
- quacq_calls, query_generation_calls, query_generation_consistency_checks
- prune_calls, prune_is_consistent_calls, findscope_calls
- findc_calls, findc_consistency_checks
- dis_gen_calls, dis_gen_consistency_checks, reduce_calls
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import statistics


def _stat4(values: List[float]) -> Tuple[float, float, float, float]:
    """Compute (mean, std, min, max) for a list of values."""
    n = len(values)
    return (
        statistics.mean(values),
        statistics.stdev(values) if n > 1 else 0.0,
        min(values),
        max(values),
    )


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for a single ConGen or QuAcq run.

    All QuAcq-specific fields default to 0/0.0 so ConGen path is unaffected.
    """
    # Core metrics
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float
    n_kb: int

    # n_mss: Optional — ConGen provides actual value, Interactive has None
    n_mss: Optional[int] = None

    # Extended profiler metrics
    congen_runtime_ms: float = 0.0
    acqmss_runtime_ms: float = 0.0
    acqmss_calls: int = 0
    reduce_runtime_ms: float = 0.0
    solver_time_ms: float = 0.0
    is_consistent_calls: int = 0
    is_consistent_test_cases_calls: int = 0
    redundancy_consistency_checks: int = 0

    # QuAcq-specific runtime metrics (ms)
    quacq_runtime_ms: float = 0.0
    query_generation_runtime_ms: float = 0.0
    findscope_runtime_ms: float = 0.0
    findc_runtime_ms: float = 0.0
    dis_gen_runtime_ms: float = 0.0

    # QuAcq-specific call counts
    quacq_calls: int = 0
    query_generation_calls: int = 0
    query_generation_consistency_checks: int = 0
    prune_calls: int = 0
    prune_is_consistent_calls: int = 0
    findscope_calls: int = 0
    findc_calls: int = 0
    findc_consistency_checks: int = 0
    dis_gen_calls: int = 0
    dis_gen_consistency_checks: int = 0
    reduce_calls: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'runtime_ms': self.runtime_ms,
            'consistency_checks': self.consistency_checks,
            'memory_peak_mb': self.memory_peak_mb,
            'n_mss': self.n_mss,
            'n_kb': self.n_kb,
            'congen_runtime_ms': self.congen_runtime_ms,
            'acqmss_runtime_ms': self.acqmss_runtime_ms,
            'acqmss_calls': self.acqmss_calls,
            'reduce_runtime_ms': self.reduce_runtime_ms,
            'solver_time_ms': self.solver_time_ms,
            'is_consistent_calls': self.is_consistent_calls,
            'is_consistent_test_cases_calls': self.is_consistent_test_cases_calls,
            'redundancy_consistency_checks': self.redundancy_consistency_checks,
            # QuAcq-specific metrics (zero when unused)
            'quacq_runtime_ms': self.quacq_runtime_ms,
            'query_generation_runtime_ms': self.query_generation_runtime_ms,
            'findscope_runtime_ms': self.findscope_runtime_ms,
            'findc_runtime_ms': self.findc_runtime_ms,
            'dis_gen_runtime_ms': self.dis_gen_runtime_ms,
            'quacq_calls': self.quacq_calls,
            'query_generation_calls': self.query_generation_calls,
            'query_generation_consistency_checks': self.query_generation_consistency_checks,
            'prune_calls': self.prune_calls,
            'prune_is_consistent_calls': self.prune_is_consistent_calls,
            'findscope_calls': self.findscope_calls,
            'findc_calls': self.findc_calls,
            'findc_consistency_checks': self.findc_consistency_checks,
            'dis_gen_calls': self.dis_gen_calls,
            'dis_gen_consistency_checks': self.dis_gen_consistency_checks,
            'reduce_calls': self.reduce_calls,
        }


@dataclass
class AggregatedPerformanceMetrics:
    """
    Aggregated performance metrics across multiple ConGen or QuAcq runs.

    Each metric group has mean/std/min/max statistics.
    QuAcq-specific groups default to 0/0.0 so ConGen aggregation is unaffected.
    """
    n_runs: int

    # Runtime statistics (total)
    runtime_mean_ms: float
    runtime_std_ms: float
    runtime_min_ms: float
    runtime_max_ms: float

    # Consistency checks statistics (paper-defined)
    checks_mean: float
    checks_std: float
    checks_min: int
    checks_max: int

    # Memory statistics
    memory_mean_mb: float
    memory_max_mb: float

    # KB size statistics (n_mss_mean is None when all runs are Interactive)
    n_mss_mean: Optional[float] = None
    n_kb_mean: float = 0.0

    # ConGen runtime
    congen_runtime_mean_ms: float = 0.0
    congen_runtime_std_ms: float = 0.0
    congen_runtime_min_ms: float = 0.0
    congen_runtime_max_ms: float = 0.0

    # AcqMSS runtime
    acqmss_runtime_mean_ms: float = 0.0
    acqmss_runtime_std_ms: float = 0.0
    acqmss_runtime_min_ms: float = 0.0
    acqmss_runtime_max_ms: float = 0.0

    # AcqMSS calls
    acqmss_calls_mean: float = 0.0
    acqmss_calls_std: float = 0.0
    acqmss_calls_min: int = 0
    acqmss_calls_max: int = 0

    # Reduce runtime
    reduce_runtime_mean_ms: float = 0.0
    reduce_runtime_std_ms: float = 0.0
    reduce_runtime_min_ms: float = 0.0
    reduce_runtime_max_ms: float = 0.0

    # Solver time
    solver_time_mean_ms: float = 0.0
    solver_time_std_ms: float = 0.0
    solver_time_min_ms: float = 0.0
    solver_time_max_ms: float = 0.0

    # is_consistent calls
    is_consistent_calls_mean: float = 0.0
    is_consistent_calls_std: float = 0.0
    is_consistent_calls_min: int = 0
    is_consistent_calls_max: int = 0

    # is_consistent_test_cases calls
    is_consistent_tc_calls_mean: float = 0.0
    is_consistent_tc_calls_std: float = 0.0
    is_consistent_tc_calls_min: int = 0
    is_consistent_tc_calls_max: int = 0

    # Redundancy consistency checks
    redundancy_checks_mean: float = 0.0
    redundancy_checks_std: float = 0.0
    redundancy_checks_min: int = 0
    redundancy_checks_max: int = 0

    # QuAcq runtime groups
    quacq_runtime_mean_ms: float = 0.0
    quacq_runtime_std_ms: float = 0.0
    quacq_runtime_min_ms: float = 0.0
    quacq_runtime_max_ms: float = 0.0

    query_gen_runtime_mean_ms: float = 0.0
    query_gen_runtime_std_ms: float = 0.0
    query_gen_runtime_min_ms: float = 0.0
    query_gen_runtime_max_ms: float = 0.0

    findscope_runtime_mean_ms: float = 0.0
    findscope_runtime_std_ms: float = 0.0
    findscope_runtime_min_ms: float = 0.0
    findscope_runtime_max_ms: float = 0.0

    findc_runtime_mean_ms: float = 0.0
    findc_runtime_std_ms: float = 0.0
    findc_runtime_min_ms: float = 0.0
    findc_runtime_max_ms: float = 0.0

    dis_gen_runtime_mean_ms: float = 0.0
    dis_gen_runtime_std_ms: float = 0.0
    dis_gen_runtime_min_ms: float = 0.0
    dis_gen_runtime_max_ms: float = 0.0

    # QuAcq call count groups
    quacq_calls_mean: float = 0.0
    quacq_calls_std: float = 0.0
    quacq_calls_min: int = 0
    quacq_calls_max: int = 0

    query_gen_calls_mean: float = 0.0
    query_gen_calls_std: float = 0.0
    query_gen_calls_min: int = 0
    query_gen_calls_max: int = 0

    query_gen_checks_mean: float = 0.0
    query_gen_checks_std: float = 0.0
    query_gen_checks_min: int = 0
    query_gen_checks_max: int = 0

    prune_calls_mean: float = 0.0
    prune_calls_std: float = 0.0
    prune_calls_min: int = 0
    prune_calls_max: int = 0

    prune_ic_calls_mean: float = 0.0
    prune_ic_calls_std: float = 0.0
    prune_ic_calls_min: int = 0
    prune_ic_calls_max: int = 0

    findscope_calls_mean: float = 0.0
    findscope_calls_std: float = 0.0
    findscope_calls_min: int = 0
    findscope_calls_max: int = 0

    findc_calls_mean: float = 0.0
    findc_calls_std: float = 0.0
    findc_calls_min: int = 0
    findc_calls_max: int = 0

    findc_checks_mean: float = 0.0
    findc_checks_std: float = 0.0
    findc_checks_min: int = 0
    findc_checks_max: int = 0

    dis_gen_calls_mean: float = 0.0
    dis_gen_calls_std: float = 0.0
    dis_gen_calls_min: int = 0
    dis_gen_calls_max: int = 0

    dis_gen_checks_mean: float = 0.0
    dis_gen_checks_std: float = 0.0
    dis_gen_checks_min: int = 0
    dis_gen_checks_max: int = 0

    reduce_calls_mean: float = 0.0
    reduce_calls_std: float = 0.0
    reduce_calls_min: int = 0
    reduce_calls_max: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'n_runs': self.n_runs,
            'runtime': {
                'mean_ms': self.runtime_mean_ms,
                'std_ms': self.runtime_std_ms,
                'min_ms': self.runtime_min_ms,
                'max_ms': self.runtime_max_ms,
            },
            'consistency_checks': {
                'mean': self.checks_mean,
                'std': self.checks_std,
                'min': self.checks_min,
                'max': self.checks_max,
            },
            'memory': {
                'mean_mb': self.memory_mean_mb,
                'max_mb': self.memory_max_mb,
            },
            'kb_size': {
                'n_mss_mean': self.n_mss_mean,
                'n_kb_mean': self.n_kb_mean,
            },
            'congen_runtime': {
                'mean_ms': self.congen_runtime_mean_ms,
                'std_ms': self.congen_runtime_std_ms,
                'min_ms': self.congen_runtime_min_ms,
                'max_ms': self.congen_runtime_max_ms,
            },
            'acqmss_runtime': {
                'mean_ms': self.acqmss_runtime_mean_ms,
                'std_ms': self.acqmss_runtime_std_ms,
                'min_ms': self.acqmss_runtime_min_ms,
                'max_ms': self.acqmss_runtime_max_ms,
            },
            'acqmss_calls': {
                'mean': self.acqmss_calls_mean,
                'std': self.acqmss_calls_std,
                'min': self.acqmss_calls_min,
                'max': self.acqmss_calls_max,
            },
            'reduce_runtime': {
                'mean_ms': self.reduce_runtime_mean_ms,
                'std_ms': self.reduce_runtime_std_ms,
                'min_ms': self.reduce_runtime_min_ms,
                'max_ms': self.reduce_runtime_max_ms,
            },
            'solver_time': {
                'mean_ms': self.solver_time_mean_ms,
                'std_ms': self.solver_time_std_ms,
                'min_ms': self.solver_time_min_ms,
                'max_ms': self.solver_time_max_ms,
            },
            'is_consistent_calls': {
                'mean': self.is_consistent_calls_mean,
                'std': self.is_consistent_calls_std,
                'min': self.is_consistent_calls_min,
                'max': self.is_consistent_calls_max,
            },
            'is_consistent_test_cases_calls': {
                'mean': self.is_consistent_tc_calls_mean,
                'std': self.is_consistent_tc_calls_std,
                'min': self.is_consistent_tc_calls_min,
                'max': self.is_consistent_tc_calls_max,
            },
            'redundancy_consistency_checks': {
                'mean': self.redundancy_checks_mean,
                'std': self.redundancy_checks_std,
                'min': self.redundancy_checks_min,
                'max': self.redundancy_checks_max,
            },
            # QuAcq runtime groups
            'quacq_runtime': {
                'mean_ms': self.quacq_runtime_mean_ms,
                'std_ms': self.quacq_runtime_std_ms,
                'min_ms': self.quacq_runtime_min_ms,
                'max_ms': self.quacq_runtime_max_ms,
            },
            'query_gen_runtime': {
                'mean_ms': self.query_gen_runtime_mean_ms,
                'std_ms': self.query_gen_runtime_std_ms,
                'min_ms': self.query_gen_runtime_min_ms,
                'max_ms': self.query_gen_runtime_max_ms,
            },
            'findscope_runtime': {
                'mean_ms': self.findscope_runtime_mean_ms,
                'std_ms': self.findscope_runtime_std_ms,
                'min_ms': self.findscope_runtime_min_ms,
                'max_ms': self.findscope_runtime_max_ms,
            },
            'findc_runtime': {
                'mean_ms': self.findc_runtime_mean_ms,
                'std_ms': self.findc_runtime_std_ms,
                'min_ms': self.findc_runtime_min_ms,
                'max_ms': self.findc_runtime_max_ms,
            },
            'dis_gen_runtime': {
                'mean_ms': self.dis_gen_runtime_mean_ms,
                'std_ms': self.dis_gen_runtime_std_ms,
                'min_ms': self.dis_gen_runtime_min_ms,
                'max_ms': self.dis_gen_runtime_max_ms,
            },
            # QuAcq call count groups
            'quacq_calls': {
                'mean': self.quacq_calls_mean,
                'std': self.quacq_calls_std,
                'min': self.quacq_calls_min,
                'max': self.quacq_calls_max,
            },
            'query_gen_calls': {
                'mean': self.query_gen_calls_mean,
                'std': self.query_gen_calls_std,
                'min': self.query_gen_calls_min,
                'max': self.query_gen_calls_max,
            },
            'query_gen_checks': {
                'mean': self.query_gen_checks_mean,
                'std': self.query_gen_checks_std,
                'min': self.query_gen_checks_min,
                'max': self.query_gen_checks_max,
            },
            'prune_calls': {
                'mean': self.prune_calls_mean,
                'std': self.prune_calls_std,
                'min': self.prune_calls_min,
                'max': self.prune_calls_max,
            },
            'prune_ic_calls': {
                'mean': self.prune_ic_calls_mean,
                'std': self.prune_ic_calls_std,
                'min': self.prune_ic_calls_min,
                'max': self.prune_ic_calls_max,
            },
            'findscope_calls': {
                'mean': self.findscope_calls_mean,
                'std': self.findscope_calls_std,
                'min': self.findscope_calls_min,
                'max': self.findscope_calls_max,
            },
            'findc_calls': {
                'mean': self.findc_calls_mean,
                'std': self.findc_calls_std,
                'min': self.findc_calls_min,
                'max': self.findc_calls_max,
            },
            'findc_checks': {
                'mean': self.findc_checks_mean,
                'std': self.findc_checks_std,
                'min': self.findc_checks_min,
                'max': self.findc_checks_max,
            },
            'dis_gen_calls': {
                'mean': self.dis_gen_calls_mean,
                'std': self.dis_gen_calls_std,
                'min': self.dis_gen_calls_min,
                'max': self.dis_gen_calls_max,
            },
            'dis_gen_checks': {
                'mean': self.dis_gen_checks_mean,
                'std': self.dis_gen_checks_std,
                'min': self.dis_gen_checks_min,
                'max': self.dis_gen_checks_max,
            },
            'reduce_calls': {
                'mean': self.reduce_calls_mean,
                'std': self.reduce_calls_std,
                'min': self.reduce_calls_min,
                'max': self.reduce_calls_max,
            },
        }


def aggregate_metrics(metrics_list: List[PerformanceMetrics]) -> AggregatedPerformanceMetrics:
    """
    Aggregate performance metrics across multiple runs.

    Args:
        metrics_list: List of PerformanceMetrics from multiple runs

    Returns:
        AggregatedPerformanceMetrics with statistics

    Raises:
        ValueError: If metrics_list is empty
    """
    if not metrics_list:
        raise ValueError("Empty metrics list")

    n = len(metrics_list)

    runtimes = [m.runtime_ms for m in metrics_list]
    checks = [m.consistency_checks for m in metrics_list]
    memories = [m.memory_peak_mb for m in metrics_list]
    n_mss_list = [m.n_mss for m in metrics_list if m.n_mss is not None]
    n_kb_list = [m.n_kb for m in metrics_list]

    # Extended metrics
    congen_rt = [m.congen_runtime_ms for m in metrics_list]
    acqmss_rt = [m.acqmss_runtime_ms for m in metrics_list]
    acqmss_c = [float(m.acqmss_calls) for m in metrics_list]
    reduce_rt = [m.reduce_runtime_ms for m in metrics_list]
    solver_t = [m.solver_time_ms for m in metrics_list]
    ic_calls = [float(m.is_consistent_calls) for m in metrics_list]
    ictc_calls = [float(m.is_consistent_test_cases_calls) for m in metrics_list]
    red_checks = [float(m.redundancy_consistency_checks) for m in metrics_list]

    # QuAcq-specific metrics
    quacq_rt = [m.quacq_runtime_ms for m in metrics_list]
    qgen_rt = [m.query_generation_runtime_ms for m in metrics_list]
    fs_rt = [m.findscope_runtime_ms for m in metrics_list]
    fc_rt = [m.findc_runtime_ms for m in metrics_list]
    dg_rt = [m.dis_gen_runtime_ms for m in metrics_list]

    quacq_c = [float(m.quacq_calls) for m in metrics_list]
    qgen_c = [float(m.query_generation_calls) for m in metrics_list]
    qgen_chk = [float(m.query_generation_consistency_checks) for m in metrics_list]
    prune_c = [float(m.prune_calls) for m in metrics_list]
    prune_ic = [float(m.prune_is_consistent_calls) for m in metrics_list]
    fs_c = [float(m.findscope_calls) for m in metrics_list]
    fc_c = [float(m.findc_calls) for m in metrics_list]
    fc_chk = [float(m.findc_consistency_checks) for m in metrics_list]
    dg_c = [float(m.dis_gen_calls) for m in metrics_list]
    dg_chk = [float(m.dis_gen_consistency_checks) for m in metrics_list]
    red_c = [float(m.reduce_calls) for m in metrics_list]

    # Compute stats using helper
    cg_mean, cg_std, cg_min, cg_max = _stat4(congen_rt)
    aq_mean, aq_std, aq_min, aq_max = _stat4(acqmss_rt)
    ac_mean, ac_std, ac_min, ac_max = _stat4(acqmss_c)
    rd_mean, rd_std, rd_min, rd_max = _stat4(reduce_rt)
    st_mean, st_std, st_min, st_max = _stat4(solver_t)
    icc_mean, icc_std, icc_min, icc_max = _stat4(ic_calls)
    ictc_mean, ictc_std, ictc_min, ictc_max = _stat4(ictc_calls)
    rc_mean, rc_std, rc_min, rc_max = _stat4(red_checks)

    # QuAcq stats
    qrt_mean, qrt_std, qrt_min, qrt_max = _stat4(quacq_rt)
    qgrt_mean, qgrt_std, qgrt_min, qgrt_max = _stat4(qgen_rt)
    fsrt_mean, fsrt_std, fsrt_min, fsrt_max = _stat4(fs_rt)
    fcrt_mean, fcrt_std, fcrt_min, fcrt_max = _stat4(fc_rt)
    dgrt_mean, dgrt_std, dgrt_min, dgrt_max = _stat4(dg_rt)

    qc_mean, qc_std, qc_min, qc_max = _stat4(quacq_c)
    qgc_mean, qgc_std, qgc_min, qgc_max = _stat4(qgen_c)
    qgchk_mean, qgchk_std, qgchk_min, qgchk_max = _stat4(qgen_chk)
    pc_mean, pc_std, pc_min, pc_max = _stat4(prune_c)
    pic_mean, pic_std, pic_min, pic_max = _stat4(prune_ic)
    fsc_mean, fsc_std, fsc_min, fsc_max = _stat4(fs_c)
    fcc_mean, fcc_std, fcc_min, fcc_max = _stat4(fc_c)
    fcchk_mean, fcchk_std, fcchk_min, fcchk_max = _stat4(fc_chk)
    dgc_mean, dgc_std, dgc_min, dgc_max = _stat4(dg_c)
    dgchk_mean, dgchk_std, dgchk_min, dgchk_max = _stat4(dg_chk)
    redc_mean, redc_std, redc_min, redc_max = _stat4(red_c)

    return AggregatedPerformanceMetrics(
        n_runs=n,
        runtime_mean_ms=statistics.mean(runtimes),
        runtime_std_ms=statistics.stdev(runtimes) if n > 1 else 0.0,
        runtime_min_ms=min(runtimes),
        runtime_max_ms=max(runtimes),
        checks_mean=statistics.mean(checks),
        checks_std=statistics.stdev(checks) if n > 1 else 0.0,
        checks_min=min(checks),
        checks_max=max(checks),
        memory_mean_mb=statistics.mean(memories),
        memory_max_mb=max(memories),
        n_mss_mean=statistics.mean(n_mss_list) if n_mss_list else None,
        n_kb_mean=statistics.mean(n_kb_list),
        # Extended metrics
        congen_runtime_mean_ms=cg_mean,
        congen_runtime_std_ms=cg_std,
        congen_runtime_min_ms=cg_min,
        congen_runtime_max_ms=cg_max,
        acqmss_runtime_mean_ms=aq_mean,
        acqmss_runtime_std_ms=aq_std,
        acqmss_runtime_min_ms=aq_min,
        acqmss_runtime_max_ms=aq_max,
        acqmss_calls_mean=ac_mean,
        acqmss_calls_std=ac_std,
        acqmss_calls_min=int(ac_min),
        acqmss_calls_max=int(ac_max),
        reduce_runtime_mean_ms=rd_mean,
        reduce_runtime_std_ms=rd_std,
        reduce_runtime_min_ms=rd_min,
        reduce_runtime_max_ms=rd_max,
        solver_time_mean_ms=st_mean,
        solver_time_std_ms=st_std,
        solver_time_min_ms=st_min,
        solver_time_max_ms=st_max,
        is_consistent_calls_mean=icc_mean,
        is_consistent_calls_std=icc_std,
        is_consistent_calls_min=int(icc_min),
        is_consistent_calls_max=int(icc_max),
        is_consistent_tc_calls_mean=ictc_mean,
        is_consistent_tc_calls_std=ictc_std,
        is_consistent_tc_calls_min=int(ictc_min),
        is_consistent_tc_calls_max=int(ictc_max),
        redundancy_checks_mean=rc_mean,
        redundancy_checks_std=rc_std,
        redundancy_checks_min=int(rc_min),
        redundancy_checks_max=int(rc_max),
        # QuAcq runtime groups
        quacq_runtime_mean_ms=qrt_mean,
        quacq_runtime_std_ms=qrt_std,
        quacq_runtime_min_ms=qrt_min,
        quacq_runtime_max_ms=qrt_max,
        query_gen_runtime_mean_ms=qgrt_mean,
        query_gen_runtime_std_ms=qgrt_std,
        query_gen_runtime_min_ms=qgrt_min,
        query_gen_runtime_max_ms=qgrt_max,
        findscope_runtime_mean_ms=fsrt_mean,
        findscope_runtime_std_ms=fsrt_std,
        findscope_runtime_min_ms=fsrt_min,
        findscope_runtime_max_ms=fsrt_max,
        findc_runtime_mean_ms=fcrt_mean,
        findc_runtime_std_ms=fcrt_std,
        findc_runtime_min_ms=fcrt_min,
        findc_runtime_max_ms=fcrt_max,
        dis_gen_runtime_mean_ms=dgrt_mean,
        dis_gen_runtime_std_ms=dgrt_std,
        dis_gen_runtime_min_ms=dgrt_min,
        dis_gen_runtime_max_ms=dgrt_max,
        # QuAcq call count groups
        quacq_calls_mean=qc_mean,
        quacq_calls_std=qc_std,
        quacq_calls_min=int(qc_min),
        quacq_calls_max=int(qc_max),
        query_gen_calls_mean=qgc_mean,
        query_gen_calls_std=qgc_std,
        query_gen_calls_min=int(qgc_min),
        query_gen_calls_max=int(qgc_max),
        query_gen_checks_mean=qgchk_mean,
        query_gen_checks_std=qgchk_std,
        query_gen_checks_min=int(qgchk_min),
        query_gen_checks_max=int(qgchk_max),
        prune_calls_mean=pc_mean,
        prune_calls_std=pc_std,
        prune_calls_min=int(pc_min),
        prune_calls_max=int(pc_max),
        prune_ic_calls_mean=pic_mean,
        prune_ic_calls_std=pic_std,
        prune_ic_calls_min=int(pic_min),
        prune_ic_calls_max=int(pic_max),
        findscope_calls_mean=fsc_mean,
        findscope_calls_std=fsc_std,
        findscope_calls_min=int(fsc_min),
        findscope_calls_max=int(fsc_max),
        findc_calls_mean=fcc_mean,
        findc_calls_std=fcc_std,
        findc_calls_min=int(fcc_min),
        findc_calls_max=int(fcc_max),
        findc_checks_mean=fcchk_mean,
        findc_checks_std=fcchk_std,
        findc_checks_min=int(fcchk_min),
        findc_checks_max=int(fcchk_max),
        dis_gen_calls_mean=dgc_mean,
        dis_gen_calls_std=dgc_std,
        dis_gen_calls_min=int(dgc_min),
        dis_gen_calls_max=int(dgc_max),
        dis_gen_checks_mean=dgchk_mean,
        dis_gen_checks_std=dgchk_std,
        dis_gen_checks_min=int(dgchk_min),
        dis_gen_checks_max=int(dgchk_max),
        reduce_calls_mean=redc_mean,
        reduce_calls_std=redc_std,
        reduce_calls_min=int(redc_min),
        reduce_calls_max=int(redc_max),
    )
