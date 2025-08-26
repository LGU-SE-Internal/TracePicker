"""Registration script for TracePicker samplers with rcabench platform."""

from rcabench_platform.v2.samplers.spec import global_sampler_registry

from .samplers import TracePickerSampler


def register_tracepicker_samplers():
    """Register TracePicker samplers with the global registry."""
    registry = global_sampler_registry()

    # Register the main TracePicker sampler
    registry["tracepicker"] = TracePickerSampler


    print("✅ TracePicker samplers registered:")
    print("  - tracepicker: Standard TracePicker sampler")
    print("  - tracepicker-strict: Returns only sampled traces")


# Auto-register when module is imported
register_tracepicker_samplers()
