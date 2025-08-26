"""TracePicker sampler implementation for rcabench platform v2."""

from typing import List, Optional

from rcabench_platform.v2.logging import logger
from rcabench_platform.v2.samplers.spec import (
    SamplerArgs,
    SampleResult,
    SamplingMode,
    TraceSampler,
)

from ..algorithms.input_schema import TracingConfig
from ..core.tracepicker import TracePicker
from ..preprocessing.data_preprocessor import preprocess_raw_data
from ..utils.data_loader import load_and_convert_traces


class TracePickerSampler(TraceSampler):
    """Strict TracePicker sampler that only returns sampled traces.

    This version directly returns only the traces that TracePicker selected,
    rather than all traces with scores.
    """

    def __init__(
        self,
        buffer_size: int = 4000,
        pool_height: int = 1000,
        combination_count: int = 100,
        seed: int = 42,
    ):
        """Initialize strict TracePicker sampler."""
        self.buffer_size = buffer_size
        self.pool_height = pool_height
        self.combination_count = combination_count
        self.seed = seed

    def needs_cpu_count(self) -> Optional[int]:
        """Return number of CPU cores needed."""
        return 1

    def __call__(self, args: SamplerArgs) -> List[SampleResult]:
        """Run TracePicker and return only sampled traces."""

        if args.mode == SamplingMode.OFFLINE:
            raise NotImplementedError(
                "TracePicker does not support OFFLINE sampling mode yet."
            )

        logger.info(f"Running TracePicker (strict mode) on dataset {args.dataset}")

        try:
            # Create configuration and run TracePicker
            config = TracingConfig(
                buffer_size=self.buffer_size,
                sample_rate=args.sampling_rate,
                pool_height=self.pool_height,
                combination_count=self.combination_count,
                seed=self.seed,
            )

            # Load and process traces
            traces = load_and_convert_traces(args.input_folder)
            if not traces:
                return []

            # Run TracePicker
            tracing_input = preprocess_raw_data(traces, config)
            picker = TracePicker(config)
            result = picker.process_traces(tracing_input)

            # Return only sampled traces with score 1.0
            sample_results = []
            for trace_id in result.sampled_trace_ids:
                sample_results.append(SampleResult(trace_id=trace_id, sample_score=1.0))

            logger.info(f"TracePicker (strict) selected {len(sample_results)} traces")
            return sample_results

        except Exception as e:
            logger.error(f"TracePicker strict sampling failed: {e}")
            raise
