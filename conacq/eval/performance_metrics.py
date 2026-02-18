"""
Performance metrics collection for ConGen evaluation.

According to Table 7-8 in the paper, collect:
- #consistency_checks: Number of SAT solver calls
- runtime_ms: Execution time (ms)
- memory_peak_mb: Peak memory usage (MB)
- n_mss: MSS size before REDUCE
- n_kb: Final KB size

Extended metrics from profiler:
- congen_runtime_ms: ConGen.acquire() total time
- acqmss_runtime_ms: AcqMSS total time (sum of recursive calls)
- acqmss_calls: Number of AcqMSS recursive calls
- reduce_runtime_ms: Reduce phase time
- solver_time_ms: SAT solver total time
- is_consistent_calls: Checker.is_consistent() call count
- is_consistent_test_cases_calls: Checker.is_consistent_test_cases() call count
- redundancy_consistency_checks: Consistency checks in Reduce phase only
"""

from dataclasses import dataclass
from typing import List, Tuple
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
    Performance metrics for a single ConGen run.

    Metrics collected (Table 7-8 from paper):
    - runtime_ms: Total execution time (congen_total_time from profiler)
    - consistency_checks: Paper-defined SAT solver calls (paper_consistency_checks)
    - memory_peak_mb: Peak memory usage
    - n_mss: MSS size before REDUCE
    - n_kb: Final KB size

    Extended profiler metrics:
    - congen_runtime_ms: ConGen.acquire() time
    - acqmss_runtime_ms: AcqMSS total time (sum of recursive calls)
    - acqmss_calls: Number of AcqMSS recursive calls
    - reduce_runtime_ms: Reduce phase time
    - solver_time_ms: SAT solver total time
    - is_consistent_calls: Checker.is_consistent() call count
    - is_consistent_test_cases_calls: Checker.is_consistent_test_cases() call count
    - redundancy_consistency_checks: Consistency checks in Reduce phase only
    """
    # Core metrics
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float
    n_mss: int
    n_kb: int

    # Extended profiler metrics
    congen_runtime_ms: float = 0.0
    acqmss_runtime_ms: float = 0.0
    acqmss_calls: int = 0
    reduce_runtime_ms: float = 0.0
    solver_time_ms: float = 0.0
    is_consistent_calls: int = 0
    is_consistent_test_cases_calls: int = 0
    redundancy_consistency_checks: int = 0

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
        }


@dataclass
class AggregatedPerformanceMetrics:
    """
    Aggregated performance metrics across multiple runs.

    Useful for cross-validation where ConGen runs multiple times.
    Each metric has mean/std/min/max statistics.
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

    # KB size statistics
    n_mss_mean: float
    n_kb_mean: float

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
    n_mss_list = [m.n_mss for m in metrics_list]
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

    # Compute stats using helper
    cg_mean, cg_std, cg_min, cg_max = _stat4(congen_rt)
    aq_mean, aq_std, aq_min, aq_max = _stat4(acqmss_rt)
    ac_mean, ac_std, ac_min, ac_max = _stat4(acqmss_c)
    rd_mean, rd_std, rd_min, rd_max = _stat4(reduce_rt)
    st_mean, st_std, st_min, st_max = _stat4(solver_t)
    icc_mean, icc_std, icc_min, icc_max = _stat4(ic_calls)
    ictc_mean, ictc_std, ictc_min, ictc_max = _stat4(ictc_calls)
    rc_mean, rc_std, rc_min, rc_max = _stat4(red_checks)

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
        n_mss_mean=statistics.mean(n_mss_list),
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
    )
