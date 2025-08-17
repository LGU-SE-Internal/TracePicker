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

        # Two-pass approach: first add all spans to statistics, then build tree
        for span in trace.spans:
            label = span.span_label

            # Update performance statistics
            mean, std = self.pool.get_statistics(label)
            expected_duration += mean + 5 * std  # Conservative estimate
            actual_duration += span.duration

            # Add to pool for future statistics
            self.pool.add(label, span.duration)
            self.buffer_labels.append(label)

        # Build tree in proper order: roots first, then children
        processed_spans = set()

        # First pass: add all root nodes
        for span in trace.spans:
            if span.is_root() and span.span_id not in processed_spans:
                label = span.span_label
                tree.create_node(tag=label, identifier=span.span_id)
                processed_spans.add(span.span_id)
                logger.debug(
                    f"Added root node: {span.span_id} (parent_span_id='{span.parent_span_id}')"
                )

        # Second pass: add children, retry until all are processed or no progress
        max_iterations = len(trace.spans)  # Prevent infinite loops
        iteration = 0

        while len(processed_spans) < len(trace.spans) and iteration < max_iterations:
            added_in_iteration = 0

            for span in trace.spans:
                if span.span_id in processed_spans:
                    continue  # Already processed

                if span.is_root():
                    continue  # Should have been processed in first pass

                # Check if parent exists in tree
                if span.parent_span_id in processed_spans:
                    label = span.span_label
                    tree.create_node(
                        tag=label, identifier=span.span_id, parent=span.parent_span_id
                    )
                    processed_spans.add(span.span_id)
                    added_in_iteration += 1
                    logger.debug(
                        f"Added child node: {span.span_id} -> parent: {span.parent_span_id}"
                    )

            if added_in_iteration == 0:
                # No progress made, log remaining spans and break
                remaining_spans = [
                    s for s in trace.spans if s.span_id not in processed_spans
                ]
                logger.warning(
                    f"Could not process {len(remaining_spans)} spans in trace {trace.trace_id}:"
                )
                for span in remaining_spans:
                    parent_exists = span.parent_span_id in span_lookup
                    logger.warning(
                        f"  Span {span.span_id} -> parent {span.parent_span_id} "
                        f"(parent_exists: {parent_exists})"
                    )
                break

            iteration += 1

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
