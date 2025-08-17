#!/usr/bin/env python3
"""
Demo script for TracePicker with new data format.
This script creates synthetic parquet files in the new format for testing.
"""

import datetime
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
from rcabench_platform.v2.logging import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracepicker.algorithms.platform_adapter import tracepicker_algorithm


def create_synthetic_trace_data(
    num_traces: int = 1000, num_services: int = 5
) -> pl.DataFrame:
    """Create synthetic trace data in the new format."""

    services = [f"service-{i}" for i in range(num_services)]
    operations = ["get", "post", "put", "delete", "query", "process"]

    traces_data = []

    for trace_idx in range(num_traces):
        trace_id = f"trace-{trace_idx:06d}"

        # Create a trace with 2-6 spans
        num_spans = np.random.randint(2, 7)

        # Root span
        root_start_time = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=np.random.randint(0, 3600))

        spans_in_trace = []

        # Root span
        root_span = {
            "time": root_start_time,
            "trace_id": trace_id,
            "span_id": f"{trace_id}-span-0",
            "parent_span_id": "",  # Root has no parent
            "service_name": services[0],  # API gateway
            "span_name": "handle_request",
            "duration": int(np.random.normal(200_000_000, 50_000_000)),  # nanoseconds
            "attr.status_code": 1,  # Ok
            "attr.http.response.status_code": 200,
            "attr.http.request.content_length": np.random.randint(100, 1000),
            "attr.http.response.content_length": np.random.randint(500, 2000),
            "attr.instance": "instance-1",
        }
        spans_in_trace.append(root_span)

        # Child spans
        for span_idx in range(1, num_spans):
            parent_span_id = (
                f"{trace_id}-span-{span_idx - 1}"
                if span_idx == 1
                else f"{trace_id}-span-0"
            )

            # Some probability of error
            is_error = np.random.random() < 0.05
            status_code = 2 if is_error else 1  # Error or Ok
            http_status = np.random.choice([400, 500]) if is_error else 200

            span = {
                "time": root_start_time
                + datetime.timedelta(milliseconds=span_idx * 10),
                "trace_id": trace_id,
                "span_id": f"{trace_id}-span-{span_idx}",
                "parent_span_id": parent_span_id,
                "service_name": services[span_idx % len(services)],
                "span_name": np.random.choice(operations),
                "duration": int(
                    np.random.normal(50_000_000, 15_000_000)
                ),  # nanoseconds
                "attr.status_code": status_code,
                "attr.http.response.status_code": http_status,
                "attr.http.request.content_length": np.random.randint(50, 500),
                "attr.http.response.content_length": np.random.randint(100, 1000),
                "attr.instance": f"instance-{np.random.randint(1, 5)}",
            }
            spans_in_trace.append(span)

        traces_data.extend(spans_in_trace)

    # Convert to DataFrame
    df = pl.DataFrame(traces_data)

    # Add operation_name column (copy of span_name)
    df = df.with_columns(pl.col("span_name").alias("operation_name"))

    return df


def create_demo_dataset(
    output_folder: Path, num_normal: int = 800, num_anomal: int = 200
):
    """Create a demo dataset with normal and anomalous traces."""

    output_folder.mkdir(parents=True, exist_ok=True)

    logger.info(f"Creating demo dataset in {output_folder}")

    # Create normal traces
    logger.info(f"Creating {num_normal} normal traces")
    normal_df = create_synthetic_trace_data(num_normal)

    # Create anomalous traces (with higher error rates and longer durations)
    logger.info(f"Creating {num_anomal} anomalous traces")
    np.random.seed(42)  # Different seed for anomalous data
    anomal_df = create_synthetic_trace_data(num_anomal)

    # Make anomalous traces more obviously different
    anomal_df = anomal_df.with_columns(
        # Increase duration by 2-5x
        (pl.col("duration") * np.random.uniform(2, 5, len(anomal_df))).cast(pl.Int64),
        # Increase error rate
        pl.when(pl.col("attr.status_code") == 1)
        .then(pl.lit(2) if np.random.random() < 0.3 else pl.lit(1))
        .otherwise(pl.col("attr.status_code")),
    )

    # Save as parquet files
    normal_traces_file = output_folder / "normal_traces.parquet"
    anomal_traces_file = output_folder / "abnormal_traces.parquet"

    normal_df.write_parquet(normal_traces_file)
    anomal_df.write_parquet(anomal_traces_file)

    logger.info(f"Saved normal traces to {normal_traces_file}")
    logger.info(f"Saved anomalous traces to {anomal_traces_file}")

    # Create environment file
    now = datetime.datetime.now(datetime.timezone.utc)
    env_data = {
        "NORMAL_START": int((now - datetime.timedelta(hours=2)).timestamp()),
        "NORMAL_END": int((now - datetime.timedelta(hours=1)).timestamp()),
        "ABNORMAL_START": int((now - datetime.timedelta(hours=1)).timestamp()),
        "ABNORMAL_END": int(now.timestamp()),
        "TIMEZONE": "UTC",
    }

    env_file = output_folder / "env.json"
    with open(env_file, "w") as f:
        json.dump(env_data, f, indent=2)

    logger.info(f"Saved environment config to {env_file}")

    return normal_df, anomal_df


def main():
    """Run the demo."""

    print("TracePicker Demo with New Data Format")
    print("=" * 50)

    # Create demo dataset with realistic directory structure
    demo_folder = Path("demo_data")

    # Create a subdirectory that mimics real experiment structure
    experiment_dir = demo_folder / "demo-experiment-synthetic-traces"
    normal_df, anomal_df = create_demo_dataset(experiment_dir)

    print("\nDataset Statistics:")
    print(f"  Normal traces: {len(normal_df.select('trace_id').unique())}")
    print(f"  Anomalous traces: {len(anomal_df.select('trace_id').unique())}")
    print(f"  Total spans: {len(normal_df) + len(anomal_df)}")

    # Run TracePicker
    print("\nRunning TracePicker...")
    try:
        result = tracepicker_algorithm(
            data_folder=demo_folder,
            buffer_size=200,
            sample_rate=0.15,
            pool_height=100,
            combination_count=20,
            seed=42,
        )

        print("\nResults:")
        print(f"  Total traces processed: {result['total_traces']}")
        print(f"  Traces sampled: {result['sampled_traces']}")
        print(f"  Sampling ratio: {result['sampling_ratio']:.3f}")
        print(f"  Abnormal traces: {result['abnormal_traces']}")
        print(f"  Processing time: {result['processing_time']:.3f}s")
        print(f"    - Encoding: {result['encoding_time']:.3f}s")
        print(f"    - Sampling: {result['sampling_time']:.3f}s")
        print(f"    - Other: {result['other_time']:.3f}s")

        if result["sampled_trace_ids"]:
            print("\nFirst 10 sampled trace IDs:")
            for i, trace_id in enumerate(result["sampled_trace_ids"][:10]):
                print(f"  {i + 1}. {trace_id}")

        print("\n✅ Demo completed successfully!")
        print(f"📁 Demo data saved in: {demo_folder}")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
