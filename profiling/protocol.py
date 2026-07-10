"""Profiler contract + metric primitives (concern: protocol / ABC / no-op).

- Profiler:         @runtime_checkable structural Protocol for consumers
- AbstractProfiler: ABC for concrete implementations
- NullProfiler:     no-op implementation
- MetricType:       metric classification enum
- ProfilerError:    base exception
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class MetricType(Enum):
    """Types of metrics that can be recorded."""
    COUNTER = "counter"  # Integer counts (incremental)
    TIMER = "timer"  # Time measurements (list of durations)
    GAUGE = "gauge"  # Any value (last write wins)


class ProfilerError(Exception):
    """Base exception for profiler errors."""
    pass


@runtime_checkable
class Profiler(Protocol):
    """Structural Protocol for profiler consumers (typing construct only).

    Consumers that only call increment / record_time / timer / is_profiling
    type-annotate against this Protocol rather than AbstractProfiler. The package
    facade re-exports it as ``ProfilerProtocol``.
    """

    def increment(self, key: str, value: int = 1) -> None:
        """Increment a counter metric."""
        ...

    def record_time(self, key: str, duration: float) -> None:
        """Record a timing measurement (seconds)."""
        ...

    def timer(self, key: str):
        """Context manager for timing a code block."""
        ...

    @property
    def is_profiling(self) -> bool:
        """True when a profiling session is active."""
        ...


class AbstractProfiler(ABC):
    """
    Abstract base class for profiler implementations.

    All profilers must implement this interface to ensure consistent
    behavior across the system. This enables type safety,
    better IDE support, and easier extensibility.

    Required Methods (Abstract):
        - start(mode): Start profiling session
        - stop(): Stop profiling session
        - reset(): Reset all profiling data
        - is_profiling: Property to check if profiler is active
        - increment(key, value): Increment a counter metric
        - record_time(key, duration): Record a timing measurement
        - set_gauge(key, value): Set a gauge metric
        - timer(key): Context manager for timing code blocks

    Optional Methods (Concrete):
        - get_metric(key, default): Get a metric value safely
        - has_metric(key): Check if a metric exists

    Example Implementation:
        class MyCustomProfiler(AbstractProfiler):
            def start(self, mode=None):
                # Implementation
                pass

            def stop(self):
                # Implementation
                pass

            # ... implement other abstract methods
    """

    # ========== Lifecycle Methods ==========

    @abstractmethod
    def start(self, mode=None) -> None:
        """
        Start profiling session.

        Args:
            mode: Optional profiling mode (implementation-specific)
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop profiling session and cleanup resources."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset all profiling data."""
        pass

    @property
    @abstractmethod
    def is_profiling(self) -> bool:
        """Check if profiler is currently active."""
        pass

    # ========== Metric Recording Methods ==========

    @abstractmethod
    def increment(self, key: str, value: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            key: Metric name
            value: Amount to increment (default: 1)
        """
        pass

    @abstractmethod
    def record_time(self, key: str, duration: float) -> None:
        """
        Record a timing measurement.

        Args:
            key: Metric name
            duration: Time duration in seconds
        """
        pass

    @abstractmethod
    def set_gauge(self, key: str, value: Any) -> None:
        """
        Set a gauge metric (last write wins).

        Args:
            key: Metric name
            value: Any value to store
        """
        pass

    # ========== Context Manager ==========

    @abstractmethod
    def timer(self, key: str):
        """
        Context manager for timing code blocks.

        Args:
            key: Metric name for timing data

        Yields:
            None

        Example:
            with profiler.timer("operation"):
                # code to time
                pass
        """
        pass

    # ========== Optional Methods (Concrete) ==========

    def get_metric(self, key: str, default=None) -> Any:
        """
        Get a metric value safely.

        Args:
            key: Metric name
            default: Default value if metric doesn't exist

        Returns:
            Metric value or default
        """
        return default

    def has_metric(self, key: str) -> bool:
        """
        Check if a metric exists.

        Args:
            key: Metric name

        Returns:
            True if metric exists, False otherwise
        """
        return False

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get a snapshot of all metrics.

        Returns:
            Dictionary of all metrics (empty by default)
        """
        return {}

    def get_stats(self, key: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for timer metrics.

        Args:
            key: Metric name

        Returns:
            Dictionary with statistics or None
        """
        return None

    def to_dict(self, include_stats: bool = True) -> Dict[str, Any]:
        """
        Export profiling data as dictionary.

        Args:
            include_stats: If True, replace timer lists with statistics

        Returns:
            Dictionary of metrics (empty by default)
        """
        return {}

    def print_summary(self, include_raw_timers: bool = False) -> None:
        """
        Print profiling summary to console.

        Args:
            include_raw_timers: If True, also show individual timer values
        """
        pass

    def to_csv_row(self, columns: List[str]) -> List[str]:
        """
        Export metrics as CSV row.

        Args:
            columns: List of column names (metric keys)

        Returns:
            List of empty strings by default
        """
        return [""] * len(columns)

    def write_to_csv(self,
                     file_path: str,
                     columns: List[str],
                     create_header: bool = True) -> None:
        """
        Write profiling data to CSV file.

        Args:
            file_path: Path to CSV file
            columns: List of column names to export
            create_header: If True and file is empty, write header row
        """
        pass


class NullProfiler(AbstractProfiler):
    """
    No-op profiler for testing without side effects.

    This profiler implements the same interface as Profiler but does nothing.
    Useful for testing or when you need a profiler instance but don't want
    to track metrics.

    Usage:
        checker = ConsistencyChecker('glucose3', profiler_instance=NullProfiler())
        # No metrics will be recorded
    """

    def increment(self, key: str, value: int = 1) -> None:
        """No-op increment."""
        pass

    def record_time(self, key: str, duration: float) -> None:
        """No-op record time."""
        pass

    def set_gauge(self, key: str, value: float) -> None:
        """No-op set gauge."""
        pass

    def timer(self, key: str):
        """Context manager that does nothing."""

        class NullTimer:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        return NullTimer()

    def start(self, mode=None) -> None:
        """No-op start."""
        pass

    def stop(self) -> None:
        """No-op stop."""
        pass

    def reset(self) -> None:
        """No-op reset."""
        pass

    @property
    def is_profiling(self) -> bool:
        """Always returns False for NullProfiler."""
        return False
