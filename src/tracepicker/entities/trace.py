"""Trace and Span entity definitions for distributed tracing data."""

import copy
import json
from collections import deque
from typing import Any, Dict, List, Optional

from rcabench_platform.v2.logging import logger


class Span:
    """Represents a single span in a distributed trace."""

    def __init__(
        self,
        start_time: int,
        duration: float,
        status_code: int,
        trace_id: str,
        span_id: str,
        parent_span_id: str,
        instance: str,
        service: str,
        operation: str,
    ):
        """Initialize a Span.

        Args:
            start_time: Start timestamp of the span
            duration: Duration of the span in milliseconds
            status_code: HTTP status code or similar
            trace_id: ID of the trace this span belongs to
            span_id: Unique ID of this span
            parent_span_id: ID of the parent span, '-1' for root spans
            instance: Instance/node identifier
            service: Service name
            operation: Operation name
        """
        self.start_time = start_time
        self.duration = duration
        self.status_code = status_code
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.instance = str(instance)
        self.service = str(service)
        self.operation = str(operation)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time (duration) of the span."""
        return self.duration

    @property
    def span_label(self) -> str:
        """Get span label combining service and operation."""
        return f"{self.service}:{self.operation}"

    def is_root(self) -> bool:
        """Check if this is a root span."""
        return self.parent_span_id == "-1"

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "Span":
        """Create a Span from a dictionary record.

        Args:
            record: Dictionary containing span data

        Returns:
            Span instance
        """
        try:
            return cls(
                start_time=record["startTime"],
                duration=record["duration"],
                status_code=record["statusCode"],
                trace_id=record["traceId"],
                span_id=record["spanId"],
                parent_span_id=record["parentSpanId"],
                service=record["service"],
                instance=record["cmdb_id"],
                operation=record["operation"],
            )
        except KeyError as e:
            logger.error(f"Missing required field in span record: {e}")
            raise ValueError(f"Invalid span record: missing field {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "startTime": self.start_time,
            "duration": self.duration,
            "statusCode": self.status_code,
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "instance": self.instance,
            "service": self.service,
            "operation": self.operation,
        }

    def serialize(self) -> str:
        """Serialize span to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, span_str: str) -> "Span":
        """Deserialize span from JSON string."""
        try:
            span_dict = json.loads(span_str)
            return cls(
                start_time=span_dict["startTime"],
                duration=span_dict["duration"],
                status_code=span_dict["statusCode"],
                trace_id=span_dict["traceId"],
                span_id=span_dict["spanId"],
                parent_span_id=span_dict["parentSpanId"],
                instance=span_dict["instance"],
                service=span_dict["service"],
                operation=span_dict["operation"],
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to deserialize span: {e}")
            raise ValueError(f"Invalid span JSON: {e}")

    def __str__(self) -> str:
        """String representation of the span."""
        return (
            f"Span(traceId={self.trace_id}, spanId={self.span_id}, "
            f"parentSpanId={self.parent_span_id}, duration={self.duration}, "
            f"service={self.service}, operation={self.operation})"
        )


class Trace:
    """Represents a distributed trace consisting of multiple spans."""

    def __init__(self, trace_id: str, spans: List[Span], is_error: bool = False):
        """Initialize a Trace.

        Args:
            trace_id: Unique identifier for the trace
            spans: List of spans belonging to this trace
            is_error: Whether this trace contains errors
        """
        self.trace_id = trace_id
        self.spans = spans
        self.is_error = is_error

        # Additional attributes for anomaly detection
        self.abnormal = False
        self.durations = []

        # Validate trace structure
        self._validate()

    def _validate(self) -> None:
        """Validate trace structure."""
        if not self.spans:
            raise ValueError("Trace must contain at least one span")

        # Check if all spans belong to this trace
        for span in self.spans:
            if span.trace_id != self.trace_id:
                logger.warning(f"Span {span.span_id} has different trace_id than trace")

        # Check if there's exactly one root span
        root_spans = [span for span in self.spans if span.is_root()]
        if len(root_spans) != 1:
            logger.warning(
                f"Trace {self.trace_id} has {len(root_spans)} root spans, expected 1"
            )

    @property
    def span_count(self) -> int:
        """Get number of spans in this trace."""
        return len(self.spans)

    def get_root_span(self) -> Optional[Span]:
        """Get the root span of this trace."""
        root_spans = [span for span in self.spans if span.is_root()]
        return root_spans[0] if root_spans else None

    def get_child_spans(self, span_id: str) -> List[Span]:
        """Get all direct child spans of a given span.

        Args:
            span_id: ID of the parent span

        Returns:
            List of child spans
        """
        return [span for span in self.spans if span.parent_span_id == span_id]

    def get_spans_with_depth(self) -> List[tuple]:
        """Get spans with their depth in the trace tree.

        Returns:
            List of (span, depth) tuples in breadth-first order
        """
        root = self.get_root_span()
        if not root:
            return []

        result = []
        queue = deque([(root, 0)])

        while queue:
            current_span, current_depth = queue.popleft()
            result.append((current_span, current_depth))

            # Add child spans to queue
            child_spans = self.get_child_spans(current_span.span_id)
            for child in child_spans:
                queue.append((child, current_depth + 1))

        return result

    def get_total_duration(self) -> float:
        """Get total duration of the trace (duration of root span)."""
        root = self.get_root_span()
        return root.duration if root else 0.0

    def get_service_list(self) -> List[str]:
        """Get list of unique services in this trace."""
        return list(set(span.service for span in self.spans))

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "traceID": self.trace_id,
            "spans": [span.to_dict() for span in self.spans],
            "isError": self.is_error,
            "abnormal": self.abnormal,
            "durations": self.durations,
        }

    def serialize(self) -> str:
        """Serialize trace to JSON string."""
        trace_dict = copy.deepcopy(self.to_dict())
        return json.dumps(trace_dict)

    @classmethod
    def deserialize(cls, trace_str: str) -> "Trace":
        """Deserialize trace from JSON string."""
        try:
            trace_dict = json.loads(trace_str)
            spans = [Span(**span_data) for span_data in trace_dict["spans"]]
            trace = cls(
                trace_id=trace_dict["traceID"],
                spans=spans,
                is_error=trace_dict.get("isError", False),
            )
            trace.abnormal = trace_dict.get("abnormal", False)
            trace.durations = trace_dict.get("durations", [])
            return trace
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to deserialize trace: {e}")
            raise ValueError(f"Invalid trace JSON: {e}")

    def __str__(self) -> str:
        """String representation of the trace."""
        return (
            f"Trace(id={self.trace_id}, spans={len(self.spans)}, "
            f"is_error={self.is_error}, abnormal={self.abnormal})"
        )

    def __len__(self) -> int:
        """Get number of spans in trace."""
        return len(self.spans)
