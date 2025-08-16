"""Data preprocessing utilities for trace normalization and validation."""

import random
from typing import List

import numpy as np
from rcabench_platform.v2.logging import logger

from ..algorithms.input_schema import TracingConfig, TracingInput
from ..entities.trace import Span, Trace


class TracePreprocessor:
    """Preprocessor for trace data validation and normalization."""

    def __init__(self, config: TracingConfig):
        """Initialize the preprocessor.

        Args:
            config: Configuration parameters
        """
        self.config = config
        self._set_random_seed()

    def _set_random_seed(self) -> None:
        """Set random seed for reproducibility."""
        np.random.seed(self.config.seed)
        random.seed(self.config.seed)
        logger.info(f"Random seed set to {self.config.seed}")

    def preprocess_traces(self, traces: List[Trace]) -> TracingInput:
        """Preprocess a list of traces.

        Args:
            traces: List of raw traces

        Returns:
            TracingInput object with validated and normalized traces
        """
        logger.info(f"Preprocessing {len(traces)} traces")

        # Validate traces
        validated_traces = self._validate_traces(traces)
        logger.info(f"Validated {len(validated_traces)} traces")

        # Normalize traces
        normalized_traces = self._normalize_traces(validated_traces)
        logger.info(f"Normalized {len(normalized_traces)} traces")

        # Create input object
        tracing_input = TracingInput(
            traces=normalized_traces,
            config=self.config,
            metadata={
                "original_count": len(traces),
                "processed_count": len(normalized_traces),
                "preprocessing_info": {
                    "validation_enabled": True,
                    "normalization_enabled": True,
                },
            },
        )

        logger.info("Trace preprocessing completed successfully")
        return tracing_input

    def _validate_traces(self, traces: List[Trace]) -> List[Trace]:
        """Validate traces and filter out invalid ones.

        Args:
            traces: List of traces to validate

        Returns:
            List of valid traces
        """
        valid_traces = []
        invalid_count = 0

        for trace in traces:
            try:
                # Check if trace has spans
                if not trace.spans:
                    invalid_count += 1
                    continue

                # Check if trace has a root span
                root_span = trace.get_root_span()
                if not root_span:
                    invalid_count += 1
                    continue

                # Check for valid span structure
                if not self._validate_span_structure(trace):
                    invalid_count += 1
                    continue

                valid_traces.append(trace)

            except Exception as e:
                logger.warning(f"Invalid trace {trace.trace_id}: {e}")
                invalid_count += 1

        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} invalid traces")

        return valid_traces

    def _validate_span_structure(self, trace: Trace) -> bool:
        """Validate the span structure of a trace.

        Args:
            trace: Trace to validate

        Returns:
            True if structure is valid, False otherwise
        """
        span_ids = {span.span_id for span in trace.spans}

        for span in trace.spans:
            # Skip root spans
            if span.is_root():
                continue

            # Check if parent exists
            if span.parent_span_id not in span_ids:
                logger.debug(
                    f"Span {span.span_id} has non-existent parent {span.parent_span_id}"
                )
                return False

        return True

    def _normalize_traces(self, traces: List[Trace]) -> List[Trace]:
        """Normalize traces for consistent processing.

        Args:
            traces: List of traces to normalize

        Returns:
            List of normalized traces
        """
        normalized_traces = []

        for trace in traces:
            try:
                normalized_trace = self._normalize_single_trace(trace)
                normalized_traces.append(normalized_trace)
            except Exception as e:
                logger.warning(f"Failed to normalize trace {trace.trace_id}: {e}")

        return normalized_traces

    def _normalize_single_trace(self, trace: Trace) -> Trace:
        """Normalize a single trace.

        Args:
            trace: Trace to normalize

        Returns:
            Normalized trace
        """
        # Normalize span data
        normalized_spans = []
        for span in trace.spans:
            normalized_span = self._normalize_span(span)
            normalized_spans.append(normalized_span)

        # Create normalized trace
        normalized_trace = Trace(
            trace_id=trace.trace_id, spans=normalized_spans, is_error=trace.is_error
        )

        # Copy additional attributes
        normalized_trace.abnormal = trace.abnormal
        normalized_trace.durations = trace.durations.copy()

        return normalized_trace

    def _normalize_span(self, span: Span) -> Span:
        """Normalize a single span.

        Args:
            span: Span to normalize

        Returns:
            Normalized span
        """
        # Normalize duration (ensure non-negative)
        normalized_duration = max(0.0, span.duration)

        # Normalize string fields (strip whitespace)
        normalized_service = span.service.strip()
        normalized_operation = span.operation.strip()
        normalized_instance = span.instance.strip()

        return Span(
            start_time=span.start_time,
            duration=normalized_duration,
            status_code=span.status_code,
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            instance=normalized_instance,
            service=normalized_service,
            operation=normalized_operation,
        )


def preprocess_raw_data(traces: List[Trace], config: TracingConfig) -> TracingInput:
    """Convenience function to preprocess raw trace data.

    Args:
        traces: List of raw traces
        config: Configuration parameters

    Returns:
        TracingInput object ready for algorithm processing
    """
    preprocessor = TracePreprocessor(config)
    return preprocessor.preprocess_traces(traces)
