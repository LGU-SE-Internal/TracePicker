"""TracePicker: A trace sampling framework for distributed systems."""

__version__ = "1.0.0"
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
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["TracePicker", "Trace", "Span", "TracingInput", "TracingConfig"]
