"""Concrete Profiler implementation (concern: metrics, stats, CSV/console reporting).

ProfilerMode + multiprocess (Manager.dict) support is preserved as-is here;
it is removed later when the process executor lands.
"""
import csv
import os
import statistics
import time
from contextlib import contextmanager
from enum import Enum
from multiprocessing import Manager
from threading import Lock
from typing import Any, Dict, List, Optional, Union

from .protocol import AbstractProfiler, MetricType, ProfilerError


class ProfilerMode(Enum):
    """Operating modes for the profiler."""
    SINGLE_THREAD = "single_thread"  # For single-threaded algorithms
    MULTI_PROCESS = "multi_process"  # For multiprocessing algorithms


class Profiler(AbstractProfiler):
    """
    Thread-safe profiler with support for both single-threaded
    and multi-process environments.

    Note: Each call to Profiler() creates a new instance.
    Use get_global_profiler() to access the module-level global profiler.

    Basic Usage (Single-threaded):
        from profiling import Profiler

        # Create a new profiler instance
        profiler = Profiler()
        profiler.start()

        try:
            # Direct metric recording
            profiler.increment("counter")
            with profiler.timer("operation"):
                # ... code to time ...
                pass

            profiler.print_summary()
        finally:
            profiler.stop()

    Using Global Profiler:
        from profiling import use_global_profiler, ProfilerPreset

        # Set global profiler for all algorithms
        profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
        profiler.start()

        try:
            profiler.increment("counter")
            profiler.print_summary()
        finally:
            profiler.stop()

    Using decorators:
        from profiling import measure_time, count_calls, get_global_profiler

        class MyAlgorithm:
            def __init__(self, profiler_instance=None):
                self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

            @measure_time('my_algorithm_runtime')
            @count_calls('my_algorithm_calls')
            def find_solution(self, data):
                # Decorators automatically use self.profiler
                with self.profiler.timer("sub_operation"):
                    # ... algorithm logic ...
                    pass
                return result

    Multiprocessing Usage:

        Approach 1: Main Process Records Metrics (FastDiagP Pattern)
        -------------------------------------------------------------
        The main process coordinates workers and records all metrics.
        Workers perform computation only.

        Example:
            # Main process profiler
            main_profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
            main_profiler.start(mode=ProfilerMode.MULTI_PROCESS)

            pool = mp.Pool(processes=4)

            def worker_task(data):
                # Worker does computation only (no profiling)
                result = expensive_computation(data)
                return result

            for data in dataset:
                # Main process records metrics
                with main_profiler.timer("worker_task"):
                    future = pool.apply_async(worker_task, args=(data,))
                    result = future.get()
                    main_profiler.increment("tasks_completed")

            pool.close()
            main_profiler.stop()
            main_profiler.print_summary()

        Approach 2: Workers with Independent Profilers
        -----------------------------------------------
        Each worker creates its own Profiler instance and returns metrics
        to the main process for aggregation.

        Example:
            from profiling import Profiler

            def worker_with_profiler(task_id):
                # Each worker creates its own profiler instance
                worker_profiler = Profiler()
                worker_profiler.start()

                try:
                    worker_profiler.increment("worker_calls")

                    with worker_profiler.timer("computation"):
                        result = expensive_computation(task_id)

                    worker_profiler.stop()
                    return result, worker_profiler.to_dict()
                finally:
                    pass

            # Main process aggregates
            main_profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
            main_profiler.start()

            with mp.Pool(processes=4) as pool:
                results = pool.map(worker_with_profiler, range(10))

            # Aggregate worker metrics into main profiler
            for result, worker_metrics in results:
                calls = worker_metrics.get('worker_calls', 0)
                main_profiler.increment('total_worker_calls', calls)

                comp_stats = worker_metrics.get('computation', {})
                if isinstance(comp_stats, dict):
                    total_time = comp_stats.get('total', 0)
                    main_profiler.record_time('worker_computation', total_time)

            main_profiler.stop()
            main_profiler.print_summary()

    API Reference:
        Lifecycle:    profiler.start(mode), profiler.stop(), profiler.reset()
        Counters:     profiler.increment(key, value=1)
        Timers:       profiler.record_time(key, duration_seconds)
        Gauges:       profiler.set_gauge(key, value)
        Context:      with profiler.timer(key): ...
        Decorators:   @measure_time(key), @count_calls(key)  # Module-level, instance-aware
        Statistics:   profiler.get_stats(key), profiler.get_all_metrics()
        Export:       profiler.to_dict(), profiler.print_summary(), profiler.write_to_csv(path, columns)
        Global:       use_global_profiler(ProfilerPreset.BENCHMARK), get_global_profiler()
    """

    def __init__(self):
        """Initialize a new profiler instance (not a singleton)."""
        self._is_profiling = False
        self._mode = ProfilerMode.SINGLE_THREAD
        self._profile: Optional[Union[Dict, Any]] = None
        self._manager: Optional[Any] = None
        self._metrics_metadata: Dict[str, MetricType] = {}
        self._start_time: Optional[float] = None
        self._lock = Lock()  # Instance-level lock

    # ========== Lifecycle Management ==========

    def start(self, mode: ProfilerMode = ProfilerMode.SINGLE_THREAD) -> None:
        """
        Start profiling with specified mode.

        Args:
            mode: ProfilerMode.SINGLE_THREAD (default) or ProfilerMode.MULTI_PROCESS

                SINGLE_THREAD: Uses regular dict for metrics. Fast and simple.
                    - Use for single-threaded algorithms (FastDiag, QuickXPlain, HSDAG)
                    - Thread-safe due to GIL and explicit locks

                MULTI_PROCESS: Uses Manager.dict() for metrics. Required when
                    spawning worker processes that need to be picklable.
                    - Use for algorithms that create multiprocessing.Pool
                    - Prevents pickle errors when passing objects to workers
                    - Note: Workers have separate profiler instances and cannot
                      directly access the main process's profiler. Record metrics
                      in the main process or use explicit shared Manager.dict.
                    - Example usage: FastDiagP algorithm

        Raises:
            ProfilerError: If profiler is already running. Call stop() first.

        Example:
            # Single-threaded
            profiler.start()
            # ... run algorithm ...
            profiler.stop()

            # Multi-process (FastDiagP pattern)
            profiler.start(mode=ProfilerMode.MULTI_PROCESS)
            pool = mp.Pool(4)
            # ... use pool ...
            pool.close()
            profiler.stop()
        """
        with self._lock:
            if self._is_profiling:
                raise ProfilerError("Profiler is already running. Call stop() first.")

            self._mode = mode
            self._is_profiling = True
            self._start_time = time.perf_counter()

            if mode == ProfilerMode.MULTI_PROCESS:
                self._manager = Manager()
                self._profile = self._manager.dict()
            else:
                self._profile = {}

    def stop(self) -> None:
        """Stop profiling and cleanup resources."""
        with self._lock:
            if not self._is_profiling:
                return

            self._is_profiling = False

            # Record total profiling time
            if self._start_time is not None:
                total_time = time.perf_counter() - self._start_time
                self._profile['_profiler_total_time'] = total_time
                self._start_time = None

            # Keep profile data for export, but convert Manager.dict to regular dict BEFORE cleanup
            if self._profile is not None and hasattr(self._profile, '_getvalue'):
                self._profile = dict(self._profile)

            # Cleanup multiprocessing resources AFTER converting the dict
            if self._manager is not None:
                try:
                    self._manager.shutdown()
                except Exception:
                    pass  # Manager might be already shutdown
                self._manager = None

    def reset(self) -> None:
        """Reset all profiling data."""
        with self._lock:
            if self._profile is not None:
                self._profile.clear()
            self._metrics_metadata.clear()
            self._start_time = None

    @property
    def is_profiling(self) -> bool:
        """Check if profiler is currently active."""
        return self._is_profiling

    @property
    def mode(self) -> ProfilerMode:
        """Get current profiler mode."""
        return self._mode

    # ========== Metric Recording ==========

    def increment(self, key: str, value: int = 1) -> None:
        """
        Increment a counter metric.
        
        Args:
            key: Metric name
            value: Amount to increment (default: 1)
        """
        if not self._is_profiling:
            return

        self._register_metric(key, MetricType.COUNTER)

        with self._lock:
            self._profile[key] = self._profile.get(key, 0) + value

    def record_time(self, key: str, duration: float) -> None:
        """
        Record a timing measurement.
        
        Args:
            key: Metric name
            duration: Time duration in seconds
        """
        if not self._is_profiling:
            return

        self._register_metric(key, MetricType.TIMER)

        with self._lock:
            if key not in self._profile:
                self._profile[key] = []

            # Handle both regular dict and Manager.dict
            current = self._profile[key]
            if isinstance(current, list):
                self._profile[key] = current + [duration]
            else:
                # Manager.dict doesn't support in-place modification
                self._profile[key] = list(current) + [duration]

    def set_gauge(self, key: str, value: Any) -> None:
        """
        Set a gauge metric (last write wins).
        
        Args:
            key: Metric name
            value: Any value to store
        """
        if not self._is_profiling:
            return

        self._register_metric(key, MetricType.GAUGE)

        with self._lock:
            self._profile[key] = value

    def _register_metric(self, key: str, metric_type: MetricType) -> None:
        """
        Register metric metadata for type validation.
        
        Args:
            key: Metric name
            metric_type: Type of metric
            
        Raises:
            ProfilerError: If metric is already registered with different type
        """
        if key not in self._metrics_metadata:
            self._metrics_metadata[key] = metric_type
        elif self._metrics_metadata[key] != metric_type:
            raise ProfilerError(
                f"Metric '{key}' already registered as "
                f"{self._metrics_metadata[key].value}, "
                f"cannot use as {metric_type.value}"
            )

    @contextmanager
    def timer(self, key: str):
        """
        Context manager for timing code blocks.

        Args:
            key: Metric name for timing data

        Example:
            with profiler.timer("operation"):
                # code to time
                pass
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            if self._is_profiling:
                duration = time.perf_counter() - start
                self.record_time(key, duration)

    # ========== Data Access ==========

    def get_metric(self, key: str, default=None) -> Any:
        """
        Get a metric value safely.
        
        Args:
            key: Metric name
            default: Default value if metric doesn't exist
            
        Returns:
            Metric value or default
        """
        if self._profile is None:
            return default
        return self._profile.get(key, default)

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get a snapshot of all metrics.
        
        Returns:
            Dictionary of all metrics
        """
        if self._profile is None:
            return {}

        with self._lock:
            # Convert Manager.dict to regular dict if needed
            if hasattr(self._profile, '_getvalue'):
                return dict(self._profile)
            return dict(self._profile)

    def has_metric(self, key: str) -> bool:
        """Check if a metric exists."""
        return self._profile is not None and key in self._profile

    # ========== Statistics ==========

    def get_stats(self, key: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for timer metrics.
        
        Args:
            key: Metric name
            
        Returns:
            Dictionary with count, total, mean, min, max, median, stddev
            or None if metric is not a timer or has no data
        """
        metric_type = self._metrics_metadata.get(key)
        if metric_type != MetricType.TIMER:
            return None

        values = self.get_metric(key, [])
        if not values:
            return None

        stats = {
            'count': len(values),
            'total': sum(values),
            'mean': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
        }

        # Add median and stddev for more than 1 value
        if len(values) > 1:
            stats['median'] = statistics.median(values)
            stats['stddev'] = statistics.stdev(values)

        return stats

    # ========== Export & Display ==========

    def to_dict(self, include_stats: bool = True) -> Dict[str, Any]:
        """
        Export profiling data as dictionary.
        
        Args:
            include_stats: If True, replace timer lists with statistics
            
        Returns:
            Dictionary of metrics
        """
        result = {}
        metrics = self.get_all_metrics()

        for key, value in metrics.items():
            metric_type = self._metrics_metadata.get(key)

            if include_stats and metric_type == MetricType.TIMER:
                stats = self.get_stats(key)
                result[key] = stats if stats else value
            else:
                result[key] = value

        # Add profiler metadata
        if '_profiler_total_time' in metrics:
            result['_profiler_total_time'] = metrics['_profiler_total_time']

        return result

    def print_summary(self, include_raw_timers: bool = False) -> None:
        """
        Print profiling summary to console.
        
        Args:
            include_raw_timers: If True, also show individual timer values
        """
        if not self._profile:
            print("No profiling data available.")
            return

        data = self.to_dict(include_stats=True)

        # Group by metric type
        counters = {}
        timers = {}
        gauges = {}

        for key, value in data.items():
            metric_type = self._metrics_metadata.get(key, MetricType.GAUGE)

            if metric_type == MetricType.COUNTER:
                counters[key] = value
            elif metric_type == MetricType.TIMER:
                timers[key] = value
            else:
                gauges[key] = value

        print("\n" + "=" * 70)
        print("PROFILING SUMMARY")
        print("=" * 70)

        if '_profiler_total_time' in self._profile:
            print(f"Total profiling time: {self._profile['_profiler_total_time']:.4f}s")
            print("-" * 70)

        if counters:
            print("\n📊 COUNTERS:")
            print("-" * 70)
            for key in sorted(counters.keys()):
                value = counters[key]
                print(f"  {key:45s}: {value:>10,}")

        if timers:
            print("\n⏱️  TIMERS:")
            print("-" * 70)
            for key in sorted(timers.keys()):
                stats = timers[key]
                if isinstance(stats, dict):
                    print(f"  {key}:")
                    print(f"    Calls:  {stats['count']:>8,}  "
                          f"Total: {stats['total']:>10.4f}s  "
                          f"Mean: {stats['mean']:>10.6f}s")
                    if 'median' in stats:
                        print(f"    Min:    {stats['min']:>10.6f}s  "
                              f"Max:   {stats['max']:>10.6f}s  "
                              f"Median: {stats['median']:>10.6f}s")
                    else:
                        print(f"    Min:    {stats['min']:>10.6f}s  "
                              f"Max:   {stats['max']:>10.6f}s")

                    if include_raw_timers:
                        raw_values = self.get_metric(key, [])
                        print(f"    Values: {raw_values[:10]}" +
                              ("..." if len(raw_values) > 10 else ""))
                else:
                    print(f"  {key:45s}: {stats}")

        if gauges:
            print("\n📈 GAUGES:")
            print("-" * 70)
            for key in sorted(gauges.keys()):
                value = gauges[key]
                if isinstance(value, (list, tuple)):
                    print(f"  {key:45s}: {str(value)[:50]}")
                else:
                    print(f"  {key:45s}: {value}")

        print("=" * 70 + "\n")

    def to_csv_row(self, columns: List[str]) -> List[str]:
        """
        Export metrics as CSV row.
        
        Args:
            columns: List of column names (metric keys)
            
        Returns:
            List of string values for CSV writing
        """
        result = []
        data = self.get_all_metrics()

        for col in columns:
            value = data.get(col, "")

            if isinstance(value, list):
                # Format list as bracketed comma-separated values
                result.append(f"[{','.join(str(v) for v in value)}]")
            elif isinstance(value, dict):
                # Format dict as JSON-like string
                result.append(str(value))
            else:
                result.append(str(value))

        return result

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
        if not self._profile:
            return

        # Create directory if it doesn't exist
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.isdir(dir_name):
            os.makedirs(dir_name)

        # Check if file exists and is empty
        file_exists = os.path.exists(file_path)
        is_empty = not file_exists or os.path.getsize(file_path) == 0

        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f, delimiter=';')

            if create_header and is_empty:
                writer.writerow(columns)

            writer.writerow(self.to_csv_row(columns))


