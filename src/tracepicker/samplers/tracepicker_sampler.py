"""TracePicker sampler implementation for rcabench platform v2."""

import random
from typing import List, Optional, Tuple

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
    """TracePicker sampler supporting both ONLINE and OFFLINE sampling modes.

    ONLINE mode: Uses traditional TracePicker logic with batch processing.
    OFFLINE mode: Implements early termination when target sampling rate is reached,
                  with backfill from previous batches if needed.
    """

    def __init__(
        self,
        buffer_size: int = 4000,
        pool_height: int = 1000,
        combination_count: int = 100,
        seed: int = 42,
    ):
        """Initialize TracePicker sampler."""
        self.buffer_size = buffer_size
        self.pool_height = pool_height
        self.combination_count = combination_count
        self.seed = seed

        # Offline mode state tracking
        self.reset_offline_state()

    def needs_cpu_count(self) -> Optional[int]:
        """Return number of CPU cores needed."""
        return 1

    def reset_offline_state(self):
        """Reset offline mode tracking state."""
        self.total_traces_processed = 0
        self.total_sampled_count = 0
        self.batch_history: List[
            Tuple[List[str], List[SampleResult]]
        ] = []  # (trace_ids, sampled_results)
        self.target_total_samples = 0
        self.early_terminated = False

    def __call__(self, args: SamplerArgs) -> List[SampleResult]:
        """Run TracePicker sampling based on the specified mode."""

        if args.mode == SamplingMode.ONLINE:
            return self._run_online_mode(args)
        elif args.mode == SamplingMode.OFFLINE:
            return self._run_offline_mode(args)
        else:
            raise ValueError(f"Unsupported sampling mode: {args.mode}")

    def _run_online_mode(self, args: SamplerArgs) -> List[SampleResult]:
        """Run TracePicker in ONLINE mode (traditional batch processing)."""

        logger.info(f"Running TracePicker (ONLINE mode) on dataset {args.dataset}")

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

            logger.info(f"TracePicker (ONLINE) selected {len(sample_results)} traces")
            return sample_results

        except Exception as e:
            logger.error(f"TracePicker ONLINE sampling failed: {e}")
            raise

    def _run_offline_mode(self, args: SamplerArgs) -> List[SampleResult]:
        """Run TracePicker in OFFLINE mode with early termination and backfill."""

        logger.info(f"Running TracePicker (OFFLINE mode) on dataset {args.dataset}")

        try:
            # Reset state for new run
            self.reset_offline_state()

            # Load all traces first
            traces = load_and_convert_traces(args.input_folder)
            if not traces:
                return []

            total_traces = len(traces)
            self.target_total_samples = int(total_traces * args.sampling_rate)

            logger.info(
                f"Target total samples: {self.target_total_samples} out of {total_traces} traces"
            )

            # Create configuration
            config = TracingConfig(
                buffer_size=self.buffer_size,
                sample_rate=args.sampling_rate,
                pool_height=self.pool_height,
                combination_count=self.combination_count,
                seed=self.seed,
            )

            # Process traces in batches with early termination
            picker = TracePicker(config)
            all_sampled_results = []

            # Split traces into batches
            batches = self._split_into_batches(traces, self.buffer_size)

            for batch_idx, batch_traces in enumerate(batches):
                logger.info(
                    f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch_traces)} traces"
                )

                # Get trace IDs for this batch
                batch_trace_ids = [trace.trace_id for trace in batch_traces]

                # Process this batch
                tracing_input = preprocess_raw_data(batch_traces, config)
                result = picker.process_traces_preserve_state(tracing_input)

                # Convert to SampleResult
                batch_sampled_results = []
                for trace_id in result.sampled_trace_ids:
                    batch_sampled_results.append(
                        SampleResult(trace_id=trace_id, sample_score=1.0)
                    )

                # Update tracking state
                self.total_traces_processed += len(batch_traces)
                self.total_sampled_count += len(batch_sampled_results)
                self.batch_history.append((batch_trace_ids, batch_sampled_results))

                logger.info(
                    f"Batch {batch_idx + 1}: sampled {len(batch_sampled_results)} traces, "
                    f"total sampled: {self.total_sampled_count}/{self.target_total_samples}"
                )

                # Check for early termination
                if self.total_sampled_count >= self.target_total_samples:
                    logger.info(
                        f"Target sampling rate reached at batch {batch_idx + 1}, terminating early"
                    )
                    self.early_terminated = True

                    # Truncate current batch results if we exceeded target
                    if self.total_sampled_count > self.target_total_samples:
                        excess = self.total_sampled_count - self.target_total_samples
                        batch_sampled_results = batch_sampled_results[:-excess]
                        # Update history with truncated results
                        self.batch_history[-1] = (
                            batch_trace_ids,
                            batch_sampled_results,
                        )
                        self.total_sampled_count = self.target_total_samples

                    break

            # Collect all sampled results
            for _, batch_results in self.batch_history:
                all_sampled_results.extend(batch_results)

            # Handle case where we didn't reach target sampling rate
            if self.total_sampled_count < self.target_total_samples:
                shortage = self.target_total_samples - self.total_sampled_count
                logger.info(
                    f"Sampling shortage: {shortage} traces. Performing backfill from previous batches."
                )

                backfill_results = self._perform_backfill(shortage)
                all_sampled_results.extend(backfill_results)

            logger.info(
                f"TracePicker (OFFLINE) final result: {len(all_sampled_results)} traces sampled"
            )
            return all_sampled_results

        except Exception as e:
            logger.error(f"TracePicker OFFLINE sampling failed: {e}")
            raise

    def _split_into_batches(self, traces: List, batch_size: int) -> List[List]:
        """Split traces into batches of specified size."""
        batches = []
        for i in range(0, len(traces), batch_size):
            batches.append(traces[i : i + batch_size])
        return batches

    def _perform_backfill(self, shortage: int) -> List[SampleResult]:
        """Perform backfill sampling from previous batches when target not reached.

        Strategy:
        1. Start from the last batch and work backwards
        2. For each batch, find traces that were not sampled
        3. Randomly select from unsampled traces to fill the shortage
        """

        logger.info(f"Starting backfill process for {shortage} traces")
        random.seed(self.seed)

        backfill_results = []
        remaining_shortage = shortage

        # Work backwards through batch history
        for batch_idx in range(len(self.batch_history) - 1, -1, -1):
            if remaining_shortage <= 0:
                break

            batch_trace_ids, batch_sampled_results = self.batch_history[batch_idx]
            sampled_trace_ids = {result.trace_id for result in batch_sampled_results}

            # Find unsampled traces in this batch
            unsampled_trace_ids = [
                tid for tid in batch_trace_ids if tid not in sampled_trace_ids
            ]

            if not unsampled_trace_ids:
                logger.info(
                    f"Batch {batch_idx}: no unsampled traces available for backfill"
                )
                continue

            # Randomly select from unsampled traces
            backfill_count = min(remaining_shortage, len(unsampled_trace_ids))
            selected_trace_ids = random.sample(unsampled_trace_ids, backfill_count)

            # Create SampleResult objects with lower score to indicate backfill
            for trace_id in selected_trace_ids:
                backfill_results.append(
                    SampleResult(trace_id=trace_id, sample_score=0.5)
                )

            remaining_shortage -= backfill_count
            logger.info(
                f"Batch {batch_idx}: backfilled {backfill_count} traces, "
                f"remaining shortage: {remaining_shortage}"
            )

        if remaining_shortage > 0:
            logger.warning(
                f"Could not fulfill complete backfill requirement. "
                f"Still short by {remaining_shortage} traces."
            )

        logger.info(f"Backfill completed: added {len(backfill_results)} traces")
        return backfill_results
