"""Data loader for new format using Polars."""

import datetime
import json
import math
import time
from functools import wraps
from pathlib import Path
from typing import List

import polars as pl
from rcabench_platform.v2.logging import logger

from ..entities.trace import Span, Trace


def timeit():
    """Simple timing decorator"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logger.info(f"{func.__name__} took {end - start:.2f} seconds")
            return result

        return wrapper

    return decorator


def load_json(path: Path) -> dict:
    """Load JSON file"""
    with open(path, "r") as f:
        return json.load(f)


def tt_add_op_name(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Add operation name for Train Ticket traces"""
    return lf.with_columns(pl.col("span_name").alias("operation_name"))


def replace_enum_values(column: str, enum_values: list, start: int = 0) -> pl.Expr:
    """Replace enum string values with integers"""
    mapping_expr = pl.col(column)
    for i, value in enumerate(enum_values):
        mapping_expr = mapping_expr.str.replace(value, str(start + i))
    return mapping_expr.cast(pl.Int32)


def load_inject_time(input_folder: Path) -> datetime.datetime:
    """Load injection time from environment configuration."""
    env = load_json(path=input_folder / "env.json")

    normal_start = int(env["NORMAL_START"])
    normal_end = int(env["NORMAL_END"])
    abnormal_start = int(env["ABNORMAL_START"])
    abnormal_end = int(env["ABNORMAL_END"])

    assert normal_start < normal_end <= abnormal_start < abnormal_end

    if normal_end < abnormal_start:
        inject_time = int(math.ceil(normal_end + abnormal_start) / 2)
    else:
        inject_time = abnormal_start

    inject_time = datetime.datetime.fromtimestamp(inject_time, tz=datetime.timezone.utc)
    logger.debug(f"inject_time=`{inject_time}`")

    return inject_time


def merge_two_time_ranges(normal: pl.LazyFrame, anomal: pl.LazyFrame) -> pl.LazyFrame:
    """Merge normal and anomalous data with anomaly labels."""
    assert "anomal" not in normal.collect_schema().names()
    assert "anomal" not in anomal.collect_schema().names()

    # Get schemas and find columns that exist in one but not the other
    normal_schema = normal.collect_schema()
    anomal_schema = anomal.collect_schema()

    normal_cols = set(normal_schema.names())
    anomal_cols = set(anomal_schema.names())

    # Add missing columns to each dataframe with appropriate default values
    for col in normal_cols - anomal_cols:
        dtype = normal_schema[col]
        if dtype == pl.Int64:
            default_val = pl.lit(0, dtype=dtype)
        elif dtype == pl.Float64:
            default_val = pl.lit(0.0, dtype=dtype)
        elif dtype == pl.String:
            default_val = pl.lit("", dtype=dtype)
        else:
            default_val = pl.lit(None, dtype=dtype)
        anomal = anomal.with_columns(default_val.alias(col))

    for col in anomal_cols - normal_cols:
        dtype = anomal_schema[col]
        if dtype == pl.Int64:
            default_val = pl.lit(0, dtype=dtype)
        elif dtype == pl.Float64:
            default_val = pl.lit(0.0, dtype=dtype)
        elif dtype == pl.String:
            default_val = pl.lit("", dtype=dtype)
        else:
            default_val = pl.lit(None, dtype=dtype)
        normal = normal.with_columns(default_val.alias(col))

    # Add anomaly labels
    normal = normal.with_columns(anomal=pl.lit(0, dtype=pl.UInt8))
    anomal = anomal.with_columns(anomal=pl.lit(1, dtype=pl.UInt8))

    # Ensure column order is the same for both dataframes
    # Use the column order from normal dataframe
    final_cols = list(normal.collect_schema().names())
    normal = normal.select(final_cols)
    anomal = anomal.select(final_cols)

    merged = pl.concat([normal, anomal])
    return merged


def ui_span_name_parser(df: pl.DataFrame) -> pl.DataFrame:
    """Parse UI dashboard span names by replacing with child span names."""
    # Create a mapping from parent span ID to child span name
    child_mapping = df.select(["parent_span_id", "span_name"]).rename(
        {"parent_span_id": "span_id", "span_name": "child_span_name"}
    )

    # Join with original dataframe
    merged_df = df.join(child_mapping, on="span_id", how="left")

    # Replace span names for ts-ui-dashboard service with child span names
    processed_df = merged_df.with_columns(
        pl.when(pl.col("service_name") == "ts-ui-dashboard")
        .then(pl.col("child_span_name"))
        .otherwise(pl.col("span_name"))
        .alias("span_name")
    ).drop("child_span_name")

    return processed_df


@timeit()
def load_traces_data(input_folder: Path) -> pl.LazyFrame:
    """Load traces data from parquet files."""

    # First try to find the files directly in the input folder
    normal_traces_path = input_folder / "normal_traces.parquet"
    abnormal_traces_path = input_folder / "abnormal_traces.parquet"

    # If not found, search in subdirectories (for real experiment data structure)
    if not normal_traces_path.exists() or not abnormal_traces_path.exists():
        logger.debug(
            f"Direct files not found, searching in subdirectories of {input_folder}"
        )

        # Look for subdirectories that contain the parquet files
        for subdir in input_folder.iterdir():
            if subdir.is_dir():
                sub_normal = subdir / "normal_traces.parquet"
                sub_abnormal = subdir / "abnormal_traces.parquet"

                if sub_normal.exists() and sub_abnormal.exists():
                    logger.info(f"Found trace files in subdirectory: {subdir}")
                    normal_traces_path = sub_normal
                    abnormal_traces_path = sub_abnormal
                    break
        else:
            # Still not found, raise an error
            raise FileNotFoundError(
                f"Could not find normal_traces.parquet and abnormal_traces.parquet in {input_folder} "
                f"or any of its subdirectories"
            )

    logger.debug(f"Loading normal traces from: {normal_traces_path}")
    logger.debug(f"Loading abnormal traces from: {abnormal_traces_path}")

    normal_traces = pl.scan_parquet(normal_traces_path)
    anomal_traces = pl.scan_parquet(abnormal_traces_path)
    lf = merge_two_time_ranges(normal_traces, anomal_traces)

    lf = tt_add_op_name(lf)

    status_code_values = ["Unset", "Ok", "Error"]
    lf = lf.with_columns(
        replace_enum_values("attr.status_code", status_code_values, start=0),
    )

    lf = lf.with_columns(
        pl.col("duration").cast(pl.Float64),
        pl.col("attr.http.response.status_code").cast(pl.Float64).fill_null(200),
        pl.col("attr.http.request.content_length").cast(pl.Float64).fill_null(0),
        pl.col("attr.http.response.content_length").cast(pl.Float64).fill_null(0),
    )

    # Apply UI span name parsing
    df = lf.collect()
    df = ui_span_name_parser(df)
    lf = df.lazy()

    return lf


def polars_to_traces(df: pl.DataFrame) -> List[Trace]:
    """Convert Polars DataFrame to Trace objects."""
    logger.info(f"Converting {len(df)} spans to Trace objects")

    # Group spans by trace_id
    trace_groups = df.group_by("trace_id")
    traces = []

    for trace_id, trace_spans_df in trace_groups:
        spans = []

        # Get the actual trace_id value
        actual_trace_id = trace_id[0] if isinstance(trace_id, tuple) else trace_id

        for row in trace_spans_df.iter_rows(named=True):
            # Convert nanoseconds to milliseconds
            duration_ms = row["duration"] / 1_000_000 if row["duration"] else 0.0

            # Extract start time (convert to timestamp if needed)
            start_time = row["time"]
            if hasattr(start_time, "timestamp"):
                start_time = int(
                    start_time.timestamp() * 1000
                )  # Convert to milliseconds
            elif isinstance(start_time, (int, float)):
                start_time = int(start_time)
            else:
                start_time = 0

            # Determine status code
            status_code = 200  # Default
            if (
                "attr.http.response.status_code" in row
                and row["attr.http.response.status_code"]
            ):
                status_code = int(row["attr.http.response.status_code"])
            elif "attr.status_code" in row and row["attr.status_code"]:
                # Map status code enum to HTTP-like codes
                status_map = {0: 200, 1: 200, 2: 500}  # Unset, Ok, Error
                status_code = status_map.get(row["attr.status_code"], 200)

            # Handle parent_span_id carefully - preserve actual values
            parent_span_id = row.get("parent_span_id")
            original_parent_id = parent_span_id  # For debugging
            if parent_span_id is None:
                parent_span_id = ""
            else:
                parent_span_id = str(parent_span_id).strip()
                # Only convert truly empty strings to ""
                if parent_span_id == "null" or parent_span_id == "":
                    parent_span_id = ""

            # Debug logging for the specific trace mentioned
            if str(actual_trace_id) == "9e08a3d2697dc074f5c9cf139949cc92":
                logger.debug(
                    f"Trace {actual_trace_id}, Span {row['span_id']}: "
                    f"original_parent='{original_parent_id}' -> processed_parent='{parent_span_id}'"
                )

            span = Span(
                start_time=start_time,
                duration=duration_ms,
                status_code=status_code,
                trace_id=str(actual_trace_id),
                span_id=row["span_id"],
                parent_span_id=parent_span_id,
                instance=row.get("attr.instance", "unknown"),
                service=row["service_name"],
                operation=row["span_name"],
            )
            spans.append(span)

        # Determine if trace has errors
        is_error = any(span.status_code >= 400 for span in spans)

        # Check if this is an anomalous trace
        is_anomalous = (
            bool(trace_spans_df["anomal"][0])
            if "anomal" in trace_spans_df.columns
            else False
        )

        trace = Trace(trace_id=str(actual_trace_id), spans=spans, is_error=is_error)
        trace.abnormal = is_anomalous

        traces.append(trace)

    logger.info(f"Created {len(traces)} traces")
    return traces


@timeit()
def load_and_convert_traces(input_folder: Path) -> List[Trace]:
    """Load traces from new format and convert to Trace objects."""
    logger.info(f"Loading traces from {input_folder}")

    # Load traces data
    traces_lf = load_traces_data(input_folder)

    # Convert to DataFrame for processing
    traces_df = traces_lf.collect()

    # Convert to Trace objects
    traces = polars_to_traces(traces_df)

    return traces
