"""TracePicker algorithm adapter for rcabench platform."""

from pathlib import Path
from typing import List, Optional

from rcabench_platform.v2.algorithms.spec import (
    Algorithm,
    AlgorithmAnswer,
    AlgorithmArgs,
)
from rcabench_platform.v2.logging import logger

from ..algorithms.input_schema import TracingConfig
from ..core.tracepicker import TracePicker
from ..preprocessing.data_preprocessor import preprocess_raw_data
from ..utils.new_data_loader import load_and_convert_traces


class TracesAdapter:
    """Platform adapter for TracePicker algorithm integration."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rcabench_platform.v2.logging import logger

from ..core.tracepicker import TracePicker
from ..utils.legacy_loader import load_pickle_traces
from ..utils.new_data_loader import load_and_convert_traces
from ..utils.result_saver import TracePickerResultSaver
from .input_schema import TracingConfig, TracingInput, TracingResult


class TracesAdapter:
    """Adapter for running TracePicker on different data sources."""

    def __init__(
        self,
        buffer_size: int = 4000,
        sample_rate: float = 0.1,
        pool_height: int = 1000,
        combination_count: int = 100,
        seed: int = 42,
    ):
        """Initialize TracePicker adapter.

        Args:
            buffer_size: Buffer size for trace processing
            sample_rate: Sampling rate (0-1)
            pool_height: Pool height for encoder
            combination_count: Number of combinations for optimization
            seed: Random seed for reproducibility
        """
        self.config = TracingConfig(
            buffer_size=buffer_size,
            sample_rate=sample_rate,
            pool_height=pool_height,
            combination_count=combination_count,
            seed=seed,
        )

    def __call__(
        self,
        data_folder: Path,
        inject_time: Optional[int] = None,
        dataset: Optional[str] = None,
        anomalies: Optional[List[int]] = None,
    ) -> dict:
        """Run TracePicker on trace data.

        Args:
            data_folder: Path to folder containing trace data
            inject_time: Injection time (not used in current implementation)
            dataset: Dataset name (not used in current implementation)
            anomalies: List of anomaly indices (not used in current implementation)

        Returns:
            Dictionary with sampling results
        """
        logger.info(f"Running TracePicker on data from {data_folder}")

        try:
            # Load traces from new format
            traces = load_and_convert_traces(data_folder)

            if not traces:
                logger.warning("No traces loaded")
                return {
                    "sampled_trace_ids": [],
                    "total_traces": 0,
                    "sampled_traces": 0,
                    "sampling_ratio": 0.0,
                    "processing_time": 0.0,
                }

            # Preprocess traces
            tracing_input = preprocess_raw_data(traces, self.config)

            # Run TracePicker
            picker = TracePicker(self.config)
            result = picker.process_traces(tracing_input)

            logger.info(
                f"TracePicker completed: sampled {result.sampled_traces}/{result.total_traces} traces"
            )

            return {
                "sampled_trace_ids": result.sampled_trace_ids,
                "total_traces": result.total_traces,
                "sampled_traces": result.sampled_traces,
                "sampling_ratio": result.sampling_ratio,
                "processing_time": result.total_time,
                "encoding_time": result.encoding_time,
                "sampling_time": result.sampling_time,
                "other_time": result.other_time,
                "abnormal_traces": result.abnormal_traces,
            }

        except Exception as e:
            logger.error(f"TracePicker failed: {e}")
            raise


def tracepicker_algorithm(
    data_folder: Path,
    inject_time: Optional[int] = None,
    dataset: Optional[str] = None,
    anomalies: Optional[List[int]] = None,
    buffer_size: int = 4000,
    sample_rate: float = 0.1,
    pool_height: int = 1000,
    combination_count: int = 100,
    seed: int = 42,
    save_results: bool = True,
) -> dict:
    """Standalone TracePicker function.

    Args:
        data_folder: Path to folder containing trace data
        inject_time: Injection time (optional)
        dataset: Dataset name (optional)
        anomalies: List of anomaly indices (optional)
        buffer_size: Buffer size for trace processing
        sample_rate: Sampling rate (0-1)
        pool_height: Pool height for encoder
        combination_count: Number of combinations for optimization
        seed: Random seed for reproducibility

    Returns:
        Dictionary with sampling results
    """
    adapter = TracesAdapter(
        buffer_size=buffer_size,
        sample_rate=sample_rate,
        pool_height=pool_height,
        combination_count=combination_count,
        seed=seed,
    )

    return adapter(
        data_folder=data_folder,
        inject_time=inject_time,
        dataset=dataset,
        anomalies=anomalies,
    )


class TracePickerAlgorithm(Algorithm):
    """TracePicker algorithm for rcabench platform."""

    def needs_cpu_count(self) -> Optional[int]:
        """Return number of CPUs needed."""
        return 4

    def __call__(self, args: AlgorithmArgs) -> List[AlgorithmAnswer]:
        """Run TracePicker algorithm.

        Args:
            args: Algorithm arguments from rcabench platform

        Returns:
            List of algorithm answers
        """
        logger.info("Starting TracePicker algorithm")

        try:
            # Extract parameters from args
            data_folder = Path(args.input_folder)

            # Create adapter with default parameters
            # These could be made configurable through args if needed
            adapter = TracesAdapter(
                buffer_size=4000,
                sample_rate=0.1,
                pool_height=1000,
                combination_count=100,
                seed=42,
            )

            # Run TracePicker
            result = adapter(data_folder)

            # Create algorithm answer
            # For trace sampling, we'll return the sampling statistics
            answer = AlgorithmAnswer(
                algorithm="TracePicker",
                result={
                    "sampled_trace_ids": result["sampled_trace_ids"],
                    "sampling_statistics": {
                        "total_traces": result["total_traces"],
                        "sampled_traces": result["sampled_traces"],
                        "sampling_ratio": result["sampling_ratio"],
                        "abnormal_traces": result["abnormal_traces"],
                    },
                    "performance_metrics": {
                        "total_time": result["processing_time"],
                        "encoding_time": result["encoding_time"],
                        "sampling_time": result["sampling_time"],
                        "other_time": result["other_time"],
                    },
                },
            )

            return [answer]

        except Exception as e:
            logger.error(f"TracePicker algorithm failed: {e}")
            # Return empty result on failure
            return [
                AlgorithmAnswer(
                    algorithm="TracePicker",
                    result={
                        "error": str(e),
                        "sampled_trace_ids": [],
                        "sampling_statistics": {
                            "total_traces": 0,
                            "sampled_traces": 0,
                            "sampling_ratio": 0.0,
                            "abnormal_traces": 0,
                        },
                    },
                )
            ]
