"""Shared buffer for storing traces grouped by encoded paths."""

from collections import defaultdict
from typing import Dict, List, Optional

from rcabench_platform.v2.logging import logger

from ..entities.trace import Trace


class SharedBuffer:
    """Buffer for storing traces grouped by their encoded path signatures."""

    def __init__(self):
        """Initialize the shared buffer."""
        self._trace_map: Dict[str, List[Trace]] = defaultdict(list)
        self._count = 0

    def __len__(self) -> int:
        """Get total number of traces in buffer."""
        return self._count

    @property
    def count(self) -> int:
        """Get total number of traces in buffer."""
        return self._count

    def add(self, code: str, trace: Trace, is_abnormal: bool) -> None:
        """Add a trace to the buffer.

        Args:
            code: Encoded path signature for the trace
            trace: Trace object to add
            is_abnormal: Whether the trace is detected as abnormal
        """
        trace.abnormal = is_abnormal
        self._trace_map[code].append(trace)
        self._count += 1

        logger.debug(
            f"Added trace {trace.trace_id} with code {code} (abnormal: {is_abnormal})"
        )

    def clear(self) -> None:
        """Clear all traces from the buffer."""
        traces_cleared = self._count
        self._trace_map.clear()
        self._count = 0

        logger.debug(f"Cleared {traces_cleared} traces from buffer")

    def get_codes(self) -> List[str]:
        """Get all unique path codes in the buffer.

        Returns:
            List of path codes
        """
        return list(self._trace_map.keys())

    def get_traces_by_code(self, code: Optional[str] = None) -> List[Trace]:
        """Get traces by path code.

        Args:
            code: Path code to filter by. If None, returns all traces.

        Returns:
            List of traces
        """
        if code is None:
            # Return all traces
            all_traces = []
            for traces in self._trace_map.values():
                all_traces.extend(traces)
            return all_traces
        else:
            return self._trace_map[code]

    def count_by_code(self, code: str) -> int:
        """Get number of traces for a specific path code.

        Args:
            code: Path code to count

        Returns:
            Number of traces with that code
        """
        return len(self._trace_map[code])

    def remove_trace(self, code: str, trace: Trace) -> None:
        """Remove a specific trace from the buffer.

        Args:
            code: Path code of the trace
            trace: Trace to remove
        """
        try:
            self._trace_map[code].remove(trace)
            self._count -= 1

            # Remove code key if no traces left
            if len(self._trace_map[code]) == 0:
                del self._trace_map[code]

            logger.debug(f"Removed trace {trace.trace_id} with code {code}")

        except (ValueError, KeyError):
            logger.warning(f"Failed to remove trace {trace.trace_id} with code {code}")

    def get_buffer_stats(self) -> Dict[str, int]:
        """Get statistics about the buffer.

        Returns:
            Dictionary with buffer statistics
        """
        return {
            "total_traces": self._count,
            "unique_codes": len(self._trace_map),
            "avg_traces_per_code": self._count / len(self._trace_map)
            if self._trace_map
            else 0,
        }
