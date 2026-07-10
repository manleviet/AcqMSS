"""Profiler presets + factory (concern: ProfilerPreset / create_profiler)."""
from enum import Enum

from .core import Profiler
from .protocol import AbstractProfiler, NullProfiler


class ProfilerPreset(Enum):
    """
    Profiler presets for common use cases.

    DISABLED: No profiling (uses NullProfiler)
        - Zero overhead
        - No metrics collected
        - Use in production when profiling is not needed

    BENCHMARK: High-precision timing measurements
        - Focuses on accurate timing data
        - Uses perf_counter for high precision
        - Suitable for performance analysis and benchmarking
        - Collects all metrics (counters, timers, gauges)
    """
    DISABLED = "disabled"
    BENCHMARK = "benchmark"


def create_profiler(preset: ProfilerPreset) -> AbstractProfiler:
    """
    Factory function to create profiler instances from presets.

    Args:
        preset: ProfilerPreset enum value (DISABLED or BENCHMARK)

    Returns:
        AbstractProfiler instance configured for the specified preset

    Raises:
        ValueError: If preset is not recognized

    Examples:
        # Disabled profiling (zero overhead)
        profiler = create_profiler(ProfilerPreset.DISABLED)
        set_default_profiler(profiler)

        # Benchmark mode (high-precision timing)
        profiler = create_profiler(ProfilerPreset.BENCHMARK)
        profiler.start()
        # ... run benchmark ...
        profiler.stop()
        profiler.print_summary()
    """
    if preset == ProfilerPreset.DISABLED:
        return NullProfiler()
    elif preset == ProfilerPreset.BENCHMARK:
        return Profiler()
    else:
        raise ValueError(f"Unknown profiler preset: {preset}")
