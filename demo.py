#!/usr/bin/env python3
"""
Simple demo script for TracePicker.

This script demonstrates how to use TracePicker with synthetic data
when real trace data is not available.
"""

import random
import sys
from pathlib import Path

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracepicker.algorithms.input_schema import TracingConfig
from tracepicker.core.tracepicker import TracePicker
from tracepicker.entities.trace import Span, Trace
from tracepicker.preprocessing.data_preprocessor import preprocess_raw_data


def create_synthetic_span(
    trace_id: str,
    span_id: str,
    parent_id: str,
    service: str,
    operation: str,
    duration: float,
) -> Span:
    """Create a synthetic span for testing."""
    return Span(
        start_time=int(np.random.uniform(1000000, 2000000)),
        duration=duration,
        status_code=200 if random.random() > 0.05 else 500,  # 5% error rate
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_id,
        instance=f"instance-{random.randint(1, 10)}",
        service=service,
        operation=operation,
    )


def create_synthetic_trace(trace_id: str) -> Trace:
    """Create a synthetic trace with realistic structure."""
    spans = []

    # Root span (API Gateway)
    root_duration = np.random.normal(200, 50)
    root_span = create_synthetic_span(
        trace_id, "span-1", "-1", "api-gateway", "handle-request", root_duration
    )
    spans.append(root_span)

    # User service span
    user_duration = np.random.normal(50, 15)
    user_span = create_synthetic_span(
        trace_id, "span-2", "span-1", "user-service", "get-user", user_duration
    )
    spans.append(user_span)

    # Database span
    db_duration = np.random.normal(30, 10)
    db_span = create_synthetic_span(
        trace_id, "span-3", "span-2", "database", "query", db_duration
    )
    spans.append(db_span)

    # Sometimes add additional services
    if random.random() > 0.3:
        # Cache service
        cache_duration = np.random.normal(5, 2)
        cache_span = create_synthetic_span(
            trace_id, "span-4", "span-2", "cache-service", "get", cache_duration
        )
        spans.append(cache_span)

    if random.random() > 0.5:
        # Notification service
        notif_duration = np.random.normal(20, 8)
        notif_span = create_synthetic_span(
            trace_id, "span-5", "span-1", "notification-service", "send", notif_duration
        )
        spans.append(notif_span)

    # Create trace with some error probability
    is_error = any(span.status_code >= 400 for span in spans)

    return Trace(trace_id=trace_id, spans=spans, is_error=is_error)


def generate_synthetic_traces(count: int) -> list:
    """Generate a list of synthetic traces."""
    print(f"Generating {count} synthetic traces...")
    traces = []

    for i in range(count):
        trace_id = f"trace-{i:06d}"
        trace = create_synthetic_trace(trace_id)
        traces.append(trace)

    return traces


def main():
    """Run the TracePicker demo."""
    print("TracePicker Demo")
    print("=" * 50)

    # Configuration
    config = TracingConfig(
        buffer_size=1000,
        pool_height=500,
        sample_rate=0.1,
        combination_count=50,
        seed=42,
    )

    print("Configuration:")
    print(f"  Buffer size: {config.buffer_size}")
    print(f"  Sample rate: {config.sample_rate}")
    print(f"  Seed: {config.seed}")
    print()

    # Generate synthetic data
    traces = generate_synthetic_traces(5000)
    print(f"Generated {len(traces)} traces")

    # Show some statistics
    total_spans = sum(len(trace.spans) for trace in traces)
    error_traces = sum(1 for trace in traces if trace.is_error)
    avg_spans = total_spans / len(traces)

    print("Statistics:")
    print(f"  Total spans: {total_spans}")
    print(f"  Average spans per trace: {avg_spans:.1f}")
    print(f"  Error traces: {error_traces} ({error_traces / len(traces) * 100:.1f}%)")
    print()

    # Preprocess traces
    print("Preprocessing traces...")
    try:
        tracing_input = preprocess_raw_data(traces, config)
        print(f"Preprocessed {tracing_input.trace_count} traces successfully")
    except Exception as e:
        print(f"Preprocessing failed: {e}")
        return

    # Run TracePicker
    print("\nRunning TracePicker...")
    try:
        picker = TracePicker(config)
        result = picker.process_traces(tracing_input)

        print("\nResults:")
        print(f"  Total traces processed: {result.total_traces}")
        print(f"  Traces sampled: {result.sampled_traces}")
        print(f"  Sampling ratio: {result.sampling_ratio:.3f}")
        print(f"  Abnormal traces: {result.abnormal_traces}")
        print(f"  Processing time: {result.total_time:.3f}s")
        print(f"    - Encoding: {result.encoding_time:.3f}s")
        print(f"    - Sampling: {result.sampling_time:.3f}s")
        print(f"    - Other: {result.other_time:.3f}s")

        # Show some sampled trace IDs
        if result.sampled_trace_ids:
            print("\nFirst 10 sampled trace IDs:")
            for i, trace_id in enumerate(result.sampled_trace_ids[:10]):
                print(f"  {i + 1}. {trace_id}")

    except Exception as e:
        print(f"TracePicker execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
