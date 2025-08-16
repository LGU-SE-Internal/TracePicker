"""Main entry point for TracePicker application."""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from rcabench_platform.v2.logging import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracepicker import TracePicker, TracingConfig
from tracepicker.preprocessing.data_preprocessor import preprocess_raw_data
from tracepicker.utils.io_utils import load_pickle


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="TracePicker trace sampling framework")

    parser.add_argument(
        "--data_dir",
        type=str,
        default="TracePicker/data",
        help="Directory containing trace data",
    )
    parser.add_argument(
        "--dataset", type=str, default="A", help="Dataset name to process"
    )
    parser.add_argument(
        "--output_dir", type=str, default="output", help="Directory to save results"
    )
    parser.add_argument(
        "--seed", type=int, default=1, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--buffer_size", type=int, default=4000, help="Buffer size for trace processing"
    )
    parser.add_argument(
        "--pool_height", type=int, default=1000, help="Pool height for encoder"
    )
    parser.add_argument(
        "--combination_count",
        type=int,
        default=100,
        help="Number of combinations for optimization",
    )
    parser.add_argument(
        "--sample_rate", type=float, default=0.1, help="Sampling rate (0-1)"
    )

    return parser.parse_args()


def load_traces(data_path: str):
    """Load traces from pickle file."""
    try:
        traces = load_pickle(data_path)
        logger.info(f"Loaded {len(traces)} traces from {data_path}")
        return traces
    except Exception as e:
        logger.error(f"Failed to load traces from {data_path}: {e}")
        raise


def save_results(result, trace_ids, args):
    """Save sampling results to CSV files."""
    os.makedirs(args.output_dir, exist_ok=True)

    # Create decision dataframe
    decisions = [trace_id in result.sampled_trace_ids for trace_id in trace_ids]

    sample_df = pd.DataFrame({"traceId": trace_ids, "decision": decisions})

    # Create cost dataframe
    cost_df = pd.DataFrame(
        {
            "encode_t": [result.encoding_time],
            "sample_t": [result.sampling_time],
            "other_t": [result.other_time],
            "total_t": [result.total_time],
        }
    )

    # Save files
    sample_file = f"{args.output_dir}/{args.dataset}-TracePicker-sample.csv"
    cost_file = f"{args.output_dir}/{args.dataset}-TracePicker-cost.csv"

    sample_df.to_csv(sample_file, index=False)
    cost_df.to_csv(cost_file, index=False)

    logger.info(f"Results saved to {sample_file} and {cost_file}")

    # Log summary
    logger.info("Processing Summary:")
    logger.info(f"  Total traces: {result.total_traces}")
    logger.info(f"  Sampled traces: {result.sampled_traces}")
    logger.info(f"  Sampling ratio: {result.sampling_ratio:.3f}")
    logger.info(f"  Abnormal traces: {result.abnormal_traces}")
    logger.info(f"  Total processing time: {result.total_time:.3f}s")


def main():
    """Main application entry point."""
    args = parse_arguments()

    logger.info("Starting TracePicker application")
    logger.info(f"Arguments: {vars(args)}")

    try:
        # Load trace data
        data_path = f"{args.data_dir}/{args.dataset}/traces.pkl"
        traces = load_traces(data_path)

        # Create configuration
        config = TracingConfig(
            buffer_size=args.buffer_size,
            pool_height=args.pool_height,
            sample_rate=args.sample_rate,
            combination_count=args.combination_count,
            seed=args.seed,
        )

        # Preprocess traces
        logger.info("Preprocessing traces...")
        tracing_input = preprocess_raw_data(traces, config)

        # Initialize TracePicker
        logger.info("Initializing TracePicker...")
        picker = TracePicker(config)

        # Process traces
        logger.info("Processing traces...")
        result = picker.process_traces(tracing_input)

        # Extract trace IDs for compatibility
        trace_ids = [trace.trace_id for trace in traces]

        # Save results
        save_results(result, trace_ids, args)

        logger.info("TracePicker application completed successfully")

    except Exception as e:
        logger.error(f"Application failed: {e}")
        raise


if __name__ == "__main__":
    main()
