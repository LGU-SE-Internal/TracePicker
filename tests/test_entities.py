"""Tests for trace and span entities."""

import pytest

from src.tracepicker.entities.trace import Span, Trace


class TestSpan:
    """Test cases for Span class."""

    def test_span_creation(self):
        """Test basic span creation."""
        span = Span(
            start_time=1000000,
            duration=150.5,
            status_code=200,
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="-1",
            instance="instance-1",
            service="user-service",
            operation="get-user",
        )

        assert span.start_time == 1000000
        assert span.duration == 150.5
        assert span.status_code == 200
        assert span.trace_id == "trace-123"
        assert span.span_id == "span-456"
        assert span.parent_span_id == "-1"
        assert span.instance == "instance-1"
        assert span.service == "user-service"
        assert span.operation == "get-user"

    def test_span_properties(self):
        """Test span properties."""
        span = Span(
            start_time=1000000,
            duration=150.5,
            status_code=200,
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="-1",
            instance="instance-1",
            service="user-service",
            operation="get-user",
        )

        assert span.elapsed_time == 150.5
        assert span.span_label == "user-service:get-user"
        assert span.is_root() is True

        # Test non-root span
        child_span = Span(
            start_time=1000000,
            duration=50.0,
            status_code=200,
            trace_id="trace-123",
            span_id="span-789",
            parent_span_id="span-456",
            instance="instance-1",
            service="db-service",
            operation="query",
        )

        assert child_span.is_root() is False

    def test_span_from_record(self):
        """Test span creation from dictionary record."""
        record = {
            "startTime": 1000000,
            "duration": 150.5,
            "statusCode": 200,
            "traceId": "trace-123",
            "spanId": "span-456",
            "parentSpanId": "-1",
            "cmdb_id": "instance-1",
            "service": "user-service",
            "operation": "get-user",
        }

        span = Span.from_record(record)
        assert span.span_label == "user-service:get-user"
        assert span.is_root() is True

    def test_span_serialization(self):
        """Test span serialization and deserialization."""
        span = Span(
            start_time=1000000,
            duration=150.5,
            status_code=200,
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="-1",
            instance="instance-1",
            service="user-service",
            operation="get-user",
        )

        # Test serialization
        span_json = span.serialize()
        assert isinstance(span_json, str)

        # Test deserialization
        deserialized_span = Span.deserialize(span_json)
        assert deserialized_span.span_label == span.span_label
        assert deserialized_span.duration == span.duration


class TestTrace:
    """Test cases for Trace class."""

    def create_sample_spans(self):
        """Create sample spans for testing."""
        root_span = Span(
            start_time=1000000,
            duration=200.0,
            status_code=200,
            trace_id="trace-123",
            span_id="span-1",
            parent_span_id="-1",
            instance="instance-1",
            service="api-gateway",
            operation="handle-request",
        )

        child_span = Span(
            start_time=1000050,
            duration=100.0,
            status_code=200,
            trace_id="trace-123",
            span_id="span-2",
            parent_span_id="span-1",
            instance="instance-2",
            service="user-service",
            operation="get-user",
        )

        return [root_span, child_span]

    def test_trace_creation(self):
        """Test basic trace creation."""
        spans = self.create_sample_spans()
        trace = Trace(trace_id="trace-123", spans=spans, is_error=False)

        assert trace.trace_id == "trace-123"
        assert len(trace.spans) == 2
        assert trace.is_error is False
        assert trace.abnormal is False

    def test_trace_properties(self):
        """Test trace properties."""
        spans = self.create_sample_spans()
        trace = Trace(trace_id="trace-123", spans=spans)

        assert trace.span_count == 2
        assert len(trace) == 2

        root_span = trace.get_root_span()
        assert root_span is not None
        assert root_span.span_id == "span-1"

        child_spans = trace.get_child_spans("span-1")
        assert len(child_spans) == 1
        assert child_spans[0].span_id == "span-2"

    def test_trace_with_depth(self):
        """Test trace spans with depth calculation."""
        spans = self.create_sample_spans()
        trace = Trace(trace_id="trace-123", spans=spans)

        spans_with_depth = trace.get_spans_with_depth()
        assert len(spans_with_depth) == 2

        # Root span should have depth 0
        root_span_depth = spans_with_depth[0]
        assert root_span_depth[0].span_id == "span-1"
        assert root_span_depth[1] == 0

        # Child span should have depth 1
        child_span_depth = spans_with_depth[1]
        assert child_span_depth[0].span_id == "span-2"
        assert child_span_depth[1] == 1

    def test_trace_validation(self):
        """Test trace validation."""
        # Test empty spans
        with pytest.raises(ValueError):
            Trace(trace_id="trace-123", spans=[])

    def test_trace_serialization(self):
        """Test trace serialization and deserialization."""
        spans = self.create_sample_spans()
        trace = Trace(trace_id="trace-123", spans=spans, is_error=False)

        # Test serialization
        trace_json = trace.serialize()
        assert isinstance(trace_json, str)

        # Test deserialization
        deserialized_trace = Trace.deserialize(trace_json)
        assert deserialized_trace.trace_id == trace.trace_id
        assert len(deserialized_trace.spans) == len(trace.spans)
