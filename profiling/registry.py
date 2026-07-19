"""Global profiler registry + session (concern: get/set/use_global_profiler, session)."""
from contextlib import contextmanager

from .core import ProfilerMode
from .presets import ProfilerPreset, create_profiler
from .protocol import AbstractProfiler


def set_global_profiler(profiler_instance: AbstractProfiler) -> None:
    """
    Set the profiler used by all algorithms and checkers.

    This allows global control of profiling behavior. Set to a Profiler instance
    to enable profiling system-wide, or to NullProfiler() to disable profiling.

    Args:
        profiler_instance: Profiler instance to use globally.
    """
    global gprofiler
    gprofiler = profiler_instance


def get_global_profiler() -> AbstractProfiler:
    """
    Get the current global profiler instance.

    Returns:
        The global profiler instance (default: NullProfiler)

    Example:
        prof = get_global_profiler()
        prof.increment('custom_metric')
    """
    return gprofiler


def use_global_profiler(preset: ProfilerPreset) -> AbstractProfiler:
    """
    Create profiler from preset and set as global in one call.

    This is a convenience function that combines create_profiler() and set_profiler().

    Args:
        preset: ProfilerPreset enum value (DISABLED or BENCHMARK)

    Returns:
        The created profiler instance (already set as global)

    Example:
        # Enable benchmark profiling (replaces 2 lines with 1)
        profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
        profiler.start()
        # ... run code ...
        profiler.stop()

        # Disable profiling
        use_global_profiler(ProfilerPreset.DISABLED)
    """
    global gprofiler
    gprofiler = create_profiler(preset)
    return gprofiler


@contextmanager
def profiler_session(preset: ProfilerPreset, mode: ProfilerMode = ProfilerMode.SINGLE_THREAD):
    """Context manager for profiler lifecycle: create, reset, start, yield, stop.

    Higher-level wrapper around use_global_profiler() that manages the full
    profiling session lifecycle.

    Args:
        preset: ProfilerPreset enum value (DISABLED or BENCHMARK)
        mode: Profiling mode (SINGLE_THREAD or MULTI_PROCESS)

    Yields:
        The configured profiler instance

    Example:
        with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
            # ... run code to profile ...
            pass
        # profiler is automatically stopped
    """
    profiler = use_global_profiler(preset)
    profiler.reset()
    profiler.start(mode=mode)
    try:
        yield profiler
    finally:
        profiler.stop()


gprofiler: AbstractProfiler = use_global_profiler(ProfilerPreset.DISABLED)