"""Dynamic Programming solution for quota allocation problem."""

from typing import List, Tuple

import numpy as np
from rcabench_platform.v2.logging import logger


class QuotaAllocatorDP:
    """Dynamic Programming solver for optimal quota allocation."""

    def __init__(
        self,
        dimension: int,
        total_quota: int,
        upper_bounds: List[int],
        base_counts: List[int],
    ):
        """Initialize the quota allocator.

        Args:
            dimension: Number of path codes
            total_quota: Total quota to distribute
            upper_bounds: Maximum allowed quota for each path
            base_counts: Historical counts for each path
        """
        self.dimension = dimension
        self.total_quota = total_quota
        self.upper_bounds = upper_bounds
        self.base_counts = base_counts

        # Validate inputs
        if len(upper_bounds) != dimension or len(base_counts) != dimension:
            raise ValueError("Dimension mismatch in quota allocator inputs")

        logger.debug(
            f"Initialized QuotaAllocatorDP with dimension={dimension}, "
            f"total_quota={total_quota}"
        )

    def solve(self) -> Tuple[List[int], float]:
        """Solve the quota allocation problem using dynamic programming.

        Returns:
            Tuple of (allocation, minimum_std)
        """
        logger.info("Starting quota allocation optimization")

        # Calculate target average
        target_average = (self.total_quota + sum(self.base_counts)) / self.dimension

        # Initialize DP table
        # dp[i][s] = minimum variance when considering first i items with sum s
        dp = [
            [float("inf")] * (self.total_quota + 1) for _ in range(self.dimension + 1)
        ]
        dp[0][0] = 0

        # Fill DP table
        for i in range(1, self.dimension + 1):
            for s in range(self.total_quota + 1):
                # Try all possible allocations for item i
                max_allocation = min(self.upper_bounds[i - 1], s)
                for allocation in range(0, max_allocation + 1):
                    if s - allocation >= 0:
                        # Calculate contribution to variance
                        total_for_item = allocation + self.base_counts[i - 1]
                        variance_contribution = (total_for_item - target_average) ** 2

                        dp[i][s] = min(
                            dp[i][s], dp[i - 1][s - allocation] + variance_contribution
                        )

        # Backtrack to find solution
        solution = self._backtrack(dp, target_average)

        # Calculate minimum standard deviation
        total_counts = [sol + base for sol, base in zip(solution, self.base_counts)]
        min_std = np.std(total_counts)

        logger.info(f"Quota allocation completed. Minimum std: {min_std:.4f}")

        return solution, min_std

    def _backtrack(self, dp: List[List[float]], target_average: float) -> List[int]:
        """Backtrack through DP table to find optimal solution.

        Args:
            dp: Filled DP table
            target_average: Target average count

        Returns:
            Optimal allocation list
        """
        solution = [0] * self.dimension
        remaining_quota = self.total_quota

        for i in range(self.dimension, 0, -1):
            # Find the allocation that led to the optimal solution
            max_allocation = min(self.upper_bounds[i - 1], remaining_quota)

            for allocation in range(0, max_allocation + 1):
                if remaining_quota - allocation >= 0:
                    total_for_item = allocation + self.base_counts[i - 1]
                    variance_contribution = (total_for_item - target_average) ** 2

                    expected_value = (
                        dp[i - 1][remaining_quota - allocation] + variance_contribution
                    )

                    if abs(dp[i][remaining_quota] - expected_value) < 1e-9:
                        solution[i - 1] = allocation
                        remaining_quota -= allocation
                        break

        return solution
