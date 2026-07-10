"""Top-level ``profiling`` package — neutral infrastructure shared by
``explanation`` and ``conacq`` (both import ``profiling`` directly).

Re-exports the complete prior public surface so all import sites use
``from profiling import X``. Split by concern:
  protocol.py   — Profiler (Protocol), AbstractProfiler ABC, NullProfiler, MetricType, ProfilerError
  core.py       — Profiler concrete class, ProfilerMode
  decorators.py — measure_time, count_calls
  presets.py    — ProfilerPreset, create_profiler
  registry.py   — get/set/use_global_profiler, profiler_session

Name convention:
  Profiler         = concrete implementation (core.py)
  ProfilerProtocol = @runtime_checkable structural Protocol (protocol.py)
"""
from .protocol import (
    Profiler as ProfilerProtocol,  # structural Protocol — public as ProfilerProtocol
    AbstractProfiler,
    NullProfiler,
    MetricType,
    ProfilerError,
)
from .core import Profiler, ProfilerMode
from .decorators import measure_time, count_calls
from .presets import ProfilerPreset, create_profiler
from .registry import (
    set_global_profiler,
    get_global_profiler,
    use_global_profiler,
    profiler_session,
)

__all__ = [
    "ProfilerProtocol",
    "AbstractProfiler",
    "NullProfiler",
    "Profiler",
    "ProfilerMode",
    "MetricType",
    "ProfilerError",
    "measure_time",
    "count_calls",
    "ProfilerPreset",
    "create_profiler",
    "set_global_profiler",
    "get_global_profiler",
    "use_global_profiler",
    "profiler_session",
]
