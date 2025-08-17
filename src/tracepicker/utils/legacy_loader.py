"""Compatibility module for loading old pickle files."""

import pickle
from typing import Any

from rcabench_platform.v2.logging import logger

from ..entities.trace import Span as NewSpan

# Import the new classes
from ..entities.trace import Trace as NewTrace


class LegacySpan:
    """Legacy Span class for compatibility with old pickle files."""

    def __init__(
        self,
        startTime,
        duration,
        statusCode,
        traceId,
        spanId,
        parentSpanId,
        instance,
        service,
        operation,
    ):
        self.startTime = startTime
        self.duration = duration
        self.statusCode = statusCode
        self.traceId = traceId
        self.spanId = spanId
        self.parentSpanId = parentSpanId
        self.instance = str(instance)
        self.service = str(service)
        self.operation = str(operation)

    def getElapsedTime(self):
        return self.duration

    def getTraceId(self):
        return self.traceId

    def getSpanId(self):
        return self.spanId

    def getParentId(self):
        return self.parentSpanId

    def getSpanLabel(self):
        return str(self.service) + ":" + str(self.operation)

    def to_new_span(self) -> NewSpan:
        """Convert legacy span to new span format."""
        return NewSpan(
            start_time=self.startTime,
            duration=self.duration,
            status_code=self.statusCode,
            trace_id=self.traceId,
            span_id=self.spanId,
            parent_span_id=self.parentSpanId,
            instance=self.instance,
            service=self.service,
            operation=self.operation,
        )


class LegacyTrace:
    """Legacy Trace class for compatibility with old pickle files."""

    def __init__(self, traceID, spans, isError=False):
        self.traceID = traceID
        self.spans = spans
        self.isError = isError
        self.abnormal = False
        self.durations = []

    def getTraceID(self):
        return self.traceID

    def getSpanNum(self):
        return len(self.spans)

    def getSpans(self):
        return self.spans

    def to_new_trace(self) -> NewTrace:
        """Convert legacy trace to new trace format."""
        # Convert spans
        new_spans = []
        for span in self.spans:
            if hasattr(span, "to_new_span"):
                new_spans.append(span.to_new_span())
            else:
                # Handle case where span is already a legacy span dict
                new_span = NewSpan(
                    start_time=getattr(span, "startTime", 0),
                    duration=getattr(span, "duration", 0.0),
                    status_code=getattr(span, "statusCode", 200),
                    trace_id=getattr(span, "traceId", ""),
                    span_id=getattr(span, "spanId", ""),
                    parent_span_id=getattr(span, "parentSpanId", "-1"),
                    instance=str(getattr(span, "instance", "")),
                    service=str(getattr(span, "service", "")),
                    operation=str(getattr(span, "operation", "")),
                )
                new_spans.append(new_span)

        # Create new trace
        new_trace = NewTrace(
            trace_id=self.traceID,
            spans=new_spans,
            is_error=getattr(self, "isError", False),
        )

        # Copy additional attributes
        new_trace.abnormal = getattr(self, "abnormal", False)
        new_trace.durations = getattr(self, "durations", [])

        return new_trace


class CompatibilityUnpickler(pickle.Unpickler):
    """Custom unpickler that handles module name changes."""

    def find_class(self, module, name):
        """Override find_class to handle module renaming."""
        # Map old module names to new ones
        if module == "entity.Trace":
            if name == "Span":
                return LegacySpan
            elif name == "Trace":
                return LegacyTrace
        elif module == "Trace":
            if name == "Span":
                return LegacySpan
            elif name == "Trace":
                return LegacyTrace
        elif module.startswith("entity"):
            # Handle various entity module paths
            if name == "Span":
                return LegacySpan
            elif name == "Trace":
                return LegacyTrace

        # For other modules, use default behavior
        return super().find_class(module, name)


def load_legacy_pickle(file_path: str) -> Any:
    """Load a pickle file with legacy class compatibility.

    Args:
        file_path: Path to the pickle file

    Returns:
        Loaded and converted data
    """
    logger.info(f"Loading legacy pickle file: {file_path}")

    try:
        with open(file_path, "rb") as f:
            unpickler = CompatibilityUnpickler(f)
            data = unpickler.load()

        # Convert legacy objects to new format
        if isinstance(data, list):
            converted_data = []
            for item in data:
                if hasattr(item, "to_new_trace"):
                    converted_data.append(item.to_new_trace())
                else:
                    # Try to handle raw trace objects
                    try:
                        # Convert to legacy trace first, then to new format
                        if hasattr(item, "traceID") and hasattr(item, "spans"):
                            legacy_trace = LegacyTrace(
                                traceID=item.traceID,
                                spans=item.spans,
                                isError=getattr(item, "isError", False),
                            )
                            legacy_trace.abnormal = getattr(item, "abnormal", False)
                            legacy_trace.durations = getattr(item, "durations", [])
                            converted_data.append(legacy_trace.to_new_trace())
                        else:
                            converted_data.append(item)
                    except Exception as e:
                        logger.warning(f"Failed to convert item {type(item)}: {e}")
                        converted_data.append(item)

            logger.info(
                f"Successfully converted {len(converted_data)} traces from legacy format"
            )
            return converted_data
        else:
            # Handle single object
            if hasattr(data, "to_new_trace"):
                return data.to_new_trace()
            return data

    except Exception as e:
        logger.error(f"Failed to load legacy pickle file {file_path}: {e}")
        raise


# Create module aliases for pickle compatibility
def setup_module_aliases():
    """Set up module aliases for pickle compatibility."""
    import sys

    # Create fake modules for pickle to find
    class FakeModule:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # Create entity module
    entity_module = FakeModule(Span=LegacySpan, Trace=LegacyTrace)

    sys.modules["entity"] = entity_module
    sys.modules["entity.Trace"] = entity_module

    # Also create Trace module alias
    trace_module = FakeModule(Span=LegacySpan, Trace=LegacyTrace)
    sys.modules["Trace"] = trace_module
