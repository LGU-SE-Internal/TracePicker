"""BFS encoder for building trace trees and encoding path signatures."""

import hashlib
from typing import List, Tuple

from rcabench_platform.v2.logging import logger
from treelib import Tree

from ..entities.trace import Trace
from .pool import HistPool


class BFSEncoder:
    """Encoder that builds trace trees and generates path signatures using BFS."""

    def __init__(self, pool_height: int):
        """Initialize the BFS encoder.

        Args:
            pool_height: Height limit for the historical pool
        """
        self.pool = HistPool(height=pool_height)
        self.buffer_labels: List[str] = []

        logger.info(f"Initialized BFSEncoder with pool height: {pool_height}")

    def build_tree_and_check(self, trace: Trace) -> Tuple[Tree, bool]:
        """Build a tree representation of the trace and check for anomalies.

        Args:
            trace: Trace to process

        Returns:
            Tuple of (tree, is_abnormal)
        """
        tree = Tree()

        # Anomaly detection flags
        is_error = trace.is_error
        is_performance_degraded = False

        # Performance tracking
        expected_duration = 0.0
        actual_duration = 0.0

        # Create span lookup
        span_lookup = {span.span_id: span for span in trace.spans}

        # Build tree and collect statistics
        for span in trace.spans:
            label = span.span_label

            # Update performance statistics
            mean, std = self.pool.get_statistics(label)
            expected_duration += mean + 5 * std  # Conservative estimate
            actual_duration += span.duration

            # Add to pool for future statistics
            self.pool.add(label, span.duration)
            self.buffer_labels.append(label)

            # Skip if node already exists
            if tree.contains(span.span_id):
                continue

            # Add node to tree
            if span.is_root():
                tree.create_node(tag=label, identifier=span.span_id)
            else:
                parent_span = span_lookup.get(span.parent_span_id)
                if parent_span:
                    tree.create_node(
                        tag=label, identifier=span.span_id, parent=parent_span.span_id
                    )
                else:
                    logger.warning(
                        f"Parent span {span.parent_span_id} not found for span {span.span_id}"
                    )

        # Check for performance degradation
        is_performance_degraded = actual_duration > expected_duration

        # Combine anomaly indicators
        is_abnormal = is_error or is_performance_degraded

        logger.debug(
            f"Built tree for trace {trace.trace_id}: "
            f"error={is_error}, perf_degraded={is_performance_degraded}"
        )

        return tree, is_abnormal

    def encode_tree_bfs(self, tree: Tree) -> str:
        """Encode a tree using breadth-first search traversal.

        Args:
            tree: Tree to encode

        Returns:
            Hash of the BFS path as string
        """
        if tree.size() == 0:
            return ""

        # Get BFS traversal of node labels
        bfs_path = [
            tree.get_node(node_id).tag for node_id in tree.expand_tree(mode=Tree.WIDTH)
        ]

        # Create path string and hash it
        path_string = str(bfs_path)
        path_hash = hashlib.md5(path_string.encode()).hexdigest()

        logger.debug(f"Encoded tree with {tree.size()} nodes to hash: {path_hash}")

        return path_hash

    def get_all_labels(self) -> List[str]:
        """Get all operation labels seen by the encoder.

        Returns:
            List of all operation labels
        """
        return self.pool.get_labels()

    def get_buffer_labels(self) -> List[str]:
        """Get unique labels from current buffer.

        Returns:
            List of unique operation labels in current buffer
        """
        return list(set(self.buffer_labels))

    def clear_buffer(self) -> None:
        """Clear the buffer labels."""
        labels_cleared = len(self.buffer_labels)
        self.buffer_labels.clear()
        logger.debug(f"Cleared {labels_cleared} buffer labels")

    def get_encoder_stats(self) -> dict:
        """Get statistics about the encoder.

        Returns:
            Dictionary with encoder statistics
        """
        pool_stats = self.pool.get_pool_stats()

        return {
            "buffer_labels": len(self.buffer_labels),
            "unique_buffer_labels": len(set(self.buffer_labels)),
            "pool_stats": pool_stats,
        }
