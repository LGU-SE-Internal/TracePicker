"""Main TracePicker algorithm implementation."""

import time
from collections import Counter
from typing import Dict, List, Tuple

from rcabench_platform.v2.logging import logger

from ..algorithms.input_schema import TracingConfig, TracingInput, TracingResult
from ..algorithms.quota_allocator import QuotaAllocatorDP
from ..entities.trace import Trace
from .buffer import SharedBuffer
from .encoder import BFSEncoder


class TracePicker:
    """Main TracePicker algorithm for intelligent trace sampling."""

    def __init__(self, config: TracingConfig):
        """Initialize TracePicker with configuration.

        Args:
            config: Configuration parameters for the algorithm
        """
        self.config = config
        self.config.validate()

        # Initialize core components
        self.buffer = SharedBuffer()
        self.encoder = BFSEncoder(config.pool_height)

        # Path statistics
        self.path_counter = Counter()

        # Abnormal type tracking
        self.abnormal_types: List[str] = []

        logger.info(
            f"Initialized TracePicker with buffer_size={config.buffer_size}, "
            f"sample_rate={config.sample_rate}"
        )

    def process_traces(self, tracing_input: TracingInput) -> TracingResult:
        """Process a batch of traces and return sampling results.

        Args:
            tracing_input: Input data containing traces and configuration

        Returns:
            TracingResult with sampled trace IDs and performance metrics
        """
        logger.info(f"Processing {tracing_input.trace_count} traces")

        # Initialize tracking variables
        sampled_trace_ids = []
        total_encoding_time = 0.0
        total_sampling_time = 0.0
        total_other_time = 0.0
        abnormal_count = 0

        # Process traces one by one
        for i, trace in enumerate(tracing_input.traces):
            is_final_trace = i == len(tracing_input.traces) - 1

            # Process single trace
            trace_sampled_ids, encode_time, sample_time, other_time = (
                self._process_single_trace(trace, is_final_trace)
            )

            # Accumulate results
            sampled_trace_ids.extend(trace_sampled_ids)
            total_encoding_time += encode_time
            total_sampling_time += sample_time
            total_other_time += other_time

            if trace.abnormal:
                abnormal_count += 1

        # Create result
        result = TracingResult(
            sampled_trace_ids=sampled_trace_ids,
            encoding_time=total_encoding_time,
            sampling_time=total_sampling_time,
            other_time=total_other_time,
            total_traces=tracing_input.trace_count,
            sampled_traces=len(sampled_trace_ids),
            abnormal_traces=abnormal_count,
            metadata={
                "config": tracing_input.config,
                "path_statistics": dict(self.path_counter),
                "abnormal_types": self.abnormal_types.copy(),
            },
        )

        logger.info(
            f"Processing completed. Sampled {len(sampled_trace_ids)} out of "
            f"{tracing_input.trace_count} traces "
            f"(ratio: {result.sampling_ratio:.3f})"
        )

        return result

    def _process_single_trace(
        self, trace: Trace, is_final: bool
    ) -> Tuple[List[str], float, float, float]:
        """Process a single trace.

        Args:
            trace: Trace to process
            is_final: Whether this is the final trace in the batch

        Returns:
            Tuple of (sampled_ids, encode_time, sample_time, other_time)
        """
        # Phase 1: Encoding
        start_time = time.time()
        path_code, is_abnormal = self._encode_trace(trace)
        encode_time = time.time() - start_time

        # Phase 2: Buffer management
        start_time = time.time()
        self.buffer.add(path_code, trace, is_abnormal)
        other_time = time.time() - start_time

        # Phase 3: Sampling (if buffer is full or this is the final trace)
        sampled_ids = []
        sample_time = 0.0

        if self.buffer.count >= self.config.buffer_size or is_final:
            start_time = time.time()
            sampled_ids = self._perform_sampling()
            sample_time = time.time() - start_time

            # Clear buffer and encoder state
            self.buffer.clear()
            self.encoder.clear_buffer()

        return sampled_ids, encode_time, sample_time, other_time

    def _encode_trace(self, trace: Trace) -> Tuple[str, bool]:
        """Encode a trace to generate its path signature.

        Args:
            trace: Trace to encode

        Returns:
            Tuple of (path_code, is_abnormal)
        """
        try:
            tree, is_abnormal = self.encoder.build_tree_and_check(trace)
            path_code = self.encoder.encode_tree_bfs(tree)
            return path_code, is_abnormal
        except Exception as e:
            logger.warning(f"Failed to encode trace {trace.trace_id}: {e}")
            return "", False

    def _perform_sampling(self) -> List[str]:
        """Perform intelligent sampling on buffered traces.

        Returns:
            List of selected trace IDs
        """
        logger.info("Starting sampling process")

        sampled_ids = []
        target_sample_count = int(self.config.sample_rate * self.buffer.count)

        if target_sample_count <= 0:
            logger.info("No samples needed based on sample rate")
            return sampled_ids

        # Get trace data organized by path codes
        path_codes = self.buffer.get_codes()
        abnormal_distributions, candidate_data = self._organize_trace_data(path_codes)

        logger.info(f"Found {len(abnormal_distributions)} abnormal traces")

        # Handle abnormal traces first (always include new types)
        sampled_ids.extend(self._handle_abnormal_traces(abnormal_distributions))
        remaining_quota = target_sample_count - len(sampled_ids)

        if remaining_quota > 0:
            # Allocate quota for remaining normal traces
            normal_sampled_ids = self._sample_normal_traces(
                candidate_data, remaining_quota
            )
            sampled_ids.extend(normal_sampled_ids)

        logger.info(f"Sampling completed. Selected {len(sampled_ids)} traces")
        return sampled_ids

    def _organize_trace_data(
        self, path_codes: List[str]
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """Organize trace data by abnormal and normal categories.

        Args:
            path_codes: List of path codes in the buffer

        Returns:
            Tuple of (abnormal_trace_ids, candidate_data_by_code)
        """
        abnormal_trace_ids = []
        candidate_data = {}

        for code in path_codes:
            traces = self.buffer.get_traces_by_code(code)
            code_candidates = []

            for trace in traces:
                if trace.abnormal and hasattr(trace, "is_error"):
                    # Check if this is a new type of abnormal trace
                    abnormal_type = f"{code}-{trace.is_error}"
                    if abnormal_type not in self.abnormal_types:
                        self.abnormal_types.append(abnormal_type)
                        abnormal_trace_ids.append(trace.trace_id)
                        self.path_counter[code] += 1
                    else:
                        code_candidates.append(trace.trace_id)
                else:
                    code_candidates.append(trace.trace_id)

            if code_candidates:
                candidate_data[code] = code_candidates

        return abnormal_trace_ids, candidate_data

    def _handle_abnormal_traces(self, abnormal_trace_ids: List[str]) -> List[str]:
        """Handle abnormal traces (always include new types).

        Args:
            abnormal_trace_ids: List of abnormal trace IDs

        Returns:
            List of selected abnormal trace IDs
        """
        return abnormal_trace_ids

    def _sample_normal_traces(
        self, candidate_data: Dict[str, List[str]], quota: int
    ) -> List[str]:
        """Sample normal traces using optimization.

        Args:
            candidate_data: Dictionary mapping path codes to candidate trace IDs
            quota: Number of traces to sample

        Returns:
            List of selected trace IDs
        """
        if not candidate_data or quota <= 0:
            return []

        logger.info(
            f"Sampling {quota} normal traces from {len(candidate_data)} path codes"
        )

        try:
            # Allocate quota among path codes
            sampled_ids = self._allocate_and_optimize(candidate_data, quota)
            return sampled_ids

        except Exception as e:
            logger.error(f"Normal trace sampling failed: {e}")
            # Fallback to simple random sampling
            return self._fallback_random_sampling(candidate_data, quota)

    def _allocate_and_optimize(
        self, candidate_data: Dict[str, List[str]], quota: int
    ) -> List[str]:
        """Allocate quota and optimize trace selection.

        Args:
            candidate_data: Dictionary mapping path codes to candidate trace IDs
            quota: Total quota to allocate

        Returns:
            List of selected trace IDs
        """
        # Prepare data for quota allocation
        codes = list(candidate_data.keys())
        upper_bounds = [len(candidate_data[code]) for code in codes]
        base_counts = [self.path_counter[code] for code in codes]

        # Allocate quota using DP
        allocator = QuotaAllocatorDP(
            dimension=len(codes),
            total_quota=quota,
            upper_bounds=upper_bounds,
            base_counts=base_counts,
        )

        allocation, min_std = allocator.solve()
        logger.info(f"Quota allocation completed with std: {min_std:.4f}")

        # Update path counters
        for code, allocated in zip(codes, allocation):
            self.path_counter[code] += allocated

        # For now, use simple random selection within allocated quotas
        # In the future, this could be replaced with the full optimization
        selected_ids = []
        for code, allocated in zip(codes, allocation):
            if allocated > 0:
                candidates = candidate_data[code]
                selected = (
                    candidates[:allocated]
                    if allocated <= len(candidates)
                    else candidates
                )
                selected_ids.extend(selected)

        return selected_ids

    def _fallback_random_sampling(
        self, candidate_data: Dict[str, List[str]], quota: int
    ) -> List[str]:
        """Fallback random sampling when optimization fails.

        Args:
            candidate_data: Dictionary mapping path codes to candidate trace IDs
            quota: Number of traces to sample

        Returns:
            List of randomly selected trace IDs
        """
        logger.info("Using fallback random sampling")

        all_candidates = []
        for candidates in candidate_data.values():
            all_candidates.extend(candidates)

        if len(all_candidates) <= quota:
            return all_candidates

        import random

        return random.sample(all_candidates, quota)
