"""
Performance metrics collection for ConGen evaluation.

According to Table 7-8 in the paper, collect:
- #consistency_checks: Number of SAT solver calls
- runtime_ms: Execution time (ms)
- memory_peak_mb: Peak memory usage (MB)
- n_mss: MSS size before REDUCE
- n_kb: Final KB size
"""

from dataclasses import dataclass, field
from typing import List
import statistics


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for a single ConGen run.

    Metrics collected (Table 7-8 from paper):
    - runtime_ms: Execution time
    - consistency_checks: Number of SAT solver calls
    - memory_peak_mb: Peak memory usage
    - n_mss: MSS size before REDUCE
    - n_kb: Final KB size
    """
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float
    n_mss: int
    n_kb: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'runtime_ms': self.runtime_ms,
            'consistency_checks': self.consistency_checks,
            'memory_peak_mb': self.memory_peak_mb,
            'n_mss': self.n_mss,
            'n_kb': self.n_kb,
        }


@dataclass
class AggregatedPerformanceMetrics:
    """
    Aggregated performance metrics across multiple runs.

    Useful for cross-validation where ConGen runs multiple times.
    """
    n_runs: int

    # Runtime statistics
    runtime_mean_ms: float
    runtime_std_ms: float
    runtime_min_ms: float
    runtime_max_ms: float

    # Consistency checks statistics
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
            }
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
        n_kb_mean=statistics.mean(n_kb_list)
    )
