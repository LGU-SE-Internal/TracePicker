"""Historical pool for tracking operation latency statistics."""

from collections import deque
from typing import Dict, List, Tuple

import numpy as np
from rcabench_platform.v2.logging import logger


class HistPool:
    """Pool for storing historical latency data and computing statistics."""

    def __init__(self, height: int):
        """Initialize the historical pool.

        Args:
            height: Maximum number of samples to keep per operation label
        """
        self.limit = height
        self.data: Dict[str, deque] = {}
        self.statistics: Dict[str, Tuple[float, float]] = {}

        self._count = 0
        self._threshold = 100

        logger.info(f"Initialized HistPool with height limit: {height}")

    def __len__(self) -> int:
        """Get number of operation labels tracked."""
        return len(self.data)

    def add(self, label: str, duration: float) -> None:
        """Add a duration measurement for an operation label.

        Args:
            label: Operation label (service:operation)
            duration: Duration measurement in milliseconds
        """
        if label not in self.data:
            self.data[label] = deque(maxlen=self.limit)

        self.data[label].append(duration)
        self._count += 1

        # Periodically update statistics
        if self._count >= self._threshold:
            self._update_statistics()
            self._count = 0
            # Increase threshold gradually to reduce computation frequency
            self._threshold = min(self._threshold + 100, 2000)

    def _update_statistics(self) -> None:
        """Update mean and standard deviation for all labels."""
        updated_count = 0

        for label in self.data.keys():
            if len(self.data[label]) > 0:
                durations = list(self.data[label])
                mean = np.mean(durations)
                std = np.std(durations)
                self.statistics[label] = (mean, std)
                updated_count += 1

        logger.debug(f"Updated statistics for {updated_count} operation labels")

    def get_statistics(self, label: str) -> Tuple[float, float]:
        """Get mean and standard deviation for an operation label.

        Args:
            label: Operation label

        Returns:
            Tuple of (mean, std). Returns (0, 0) if label not found.
        """
        return self.statistics.get(label, (0.0, 0.0))

    def get_labels(self) -> List[str]:
        """Get all tracked operation labels.

        Returns:
            List of operation labels
        """
        return list(self.data.keys())

    def get_label_count(self, label: str) -> int:
        """Get number of samples for a specific label.

        Args:
            label: Operation label

        Returns:
            Number of samples
        """
        return len(self.data.get(label, []))

    def clear_label(self, label: str) -> None:
        """Clear all data for a specific label.

        Args:
            label: Operation label to clear
        """
        if label in self.data:
            del self.data[label]
        if label in self.statistics:
            del self.statistics[label]
        logger.debug(f"Cleared data for label: {label}")

    def clear_all(self) -> None:
        """Clear all data from the pool."""
        labels_cleared = len(self.data)
        self.data.clear()
        self.statistics.clear()
        self._count = 0
        logger.info(f"Cleared all data for {labels_cleared} labels")

    def get_pool_stats(self) -> Dict[str, float]:
        """Get statistics about the pool.

        Returns:
            Dictionary with pool statistics
        """
        if not self.data:
            return {"total_labels": 0, "total_samples": 0, "avg_samples_per_label": 0.0}

        total_samples = sum(len(samples) for samples in self.data.values())

        return {
            "total_labels": len(self.data),
            "total_samples": total_samples,
            "avg_samples_per_label": total_samples / len(self.data),
        }
