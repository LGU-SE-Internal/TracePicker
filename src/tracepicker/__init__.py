"""TracePicker: A trace sampling framework for distributed systems."""

__version__ = "2.0.0"
__author__ = "TracePicker Team"


# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "TracePicker":
        from .core.tracepicker import TracePicker

        return TracePicker
    elif name == "Trace":
        from .entities.trace import Trace

        return Trace
    elif name == "Span":
        from .entities.trace import Span

        return Span
    elif name == "TracingInput":
        from .algorithms.input_schema import TracingInput

        return TracingInput
    elif name == "TracingConfig":
        from .algorithms.input_schema import TracingConfig

        return TracingConfig
    elif name == "TracePickerAlgorithm":
        from .algorithms.platform_adapter import TracePickerAlgorithm

        return TracePickerAlgorithm
    elif name == "TracePickerAdapter":
        from .algorithms.platform_adapter import TracePickerAdapter

        return TracePickerAdapter
    elif name == "run_tracepicker":
        from .algorithms.platform_adapter import run_tracepicker

        return run_tracepicker
    elif name == "ResultSaver":
        from .utils.result_saver import TracepickerResultSaver

        return TracepickerResultSaver
    elif name == "TracePickerSampler":
        from .samplers.tracepicker_sampler import TracePickerSampler

        return TracePickerSampler
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "TracePicker",
    "Trace",
    "Span",
    "TracingInput",
    "TracingConfig",
    "TracePickerAlgorithm",
    "TracePickerAdapter",
    "run_tracepicker",
    "ResultSaver",
    "TracePickerSampler",
]
