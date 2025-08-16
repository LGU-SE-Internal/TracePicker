"""Sample optimization problem using genetic algorithm."""

import random
import time
from typing import List, Tuple

import numpy as np
from rcabench_platform.v2.logging import logger

try:
    import geatpy as ea

    GEATPY_AVAILABLE = True
except ImportError:
    logger.warning(
        "Geatpy not available. Sample optimization will use fallback method."
    )
    GEATPY_AVAILABLE = False


class Combination:
    """Represents a combination of trace indices."""

    def __init__(self, indices: List[int]):
        """Initialize combination.

        Args:
            indices: List of trace indices in this combination
        """
        self.indices = np.array(indices)


class SampleOptimizer:
    """Optimizer for selecting optimal trace combinations."""

    def __init__(
        self,
        raw_distributions: List[List[float]],
        abnormal_distributions: List[List[float]],
        quotas: List[int],
        base_counts: List[int],
        combination_count: int,
    ):
        """Initialize the sample optimizer.

        Args:
            raw_distributions: Latency distributions of candidate traces
            abnormal_distributions: Latency distributions of abnormal traces
            quotas: Sampling quotas for each path code
            base_counts: Number of candidates for each path code
            combination_count: Number of combinations to generate for each code
        """
        self.raw_distributions = np.array(raw_distributions)
        self.abnormal_distributions = np.array(abnormal_distributions)
        self.quotas = np.array(quotas)
        self.base_counts = np.array(base_counts)
        self.combination_count = combination_count

        # Validate inputs
        if combination_count < 2:
            raise ValueError("Combination count must be at least 2")

        self.num_labels = self.raw_distributions.shape[1]
        self.total_quota = np.sum(self.quotas)

        # Initialize combinations
        self._initialize_combinations()

        # Calculate reference percentiles
        self._calculate_reference_percentiles()

        logger.info(
            f"Initialized SampleOptimizer with {len(quotas)} path codes, "
            f"{combination_count} combinations each"
        )

    def _initialize_combinations(self) -> None:
        """Initialize random combinations for each path code."""
        logger.info("Initializing trace combinations...")
        start_time = time.time()

        splits = np.cumsum(self.base_counts)
        all_combinations = []

        for i, (start, end) in enumerate(zip([0] + list(splits[:-1]), splits)):
            if self.quotas[i] > 0 and end > start:
                combinations = []
                for _ in range(self.combination_count):
                    if self.quotas[i] <= (end - start):
                        indices = random.sample(range(start, end), self.quotas[i])
                        combinations.append(Combination(indices))
                    else:
                        # If quota exceeds available traces, take all
                        indices = list(range(start, end))
                        combinations.append(Combination(indices))

                all_combinations.append(combinations)
            else:
                # Empty combinations for zero quota
                all_combinations.append(
                    [Combination([]) for _ in range(self.combination_count)]
                )

        self.all_combinations = np.array(
            all_combinations
        ).T  # (combination_count, num_codes)

        end_time = time.time()
        logger.info(
            f"Combination initialization completed in {end_time - start_time:.2f} seconds"
        )

    def _calculate_reference_percentiles(self) -> None:
        """Calculate reference percentiles from original data."""
        self.percentiles = [0, 25, 50, 75, 90, 95, 99, 100]

        # Combine raw and abnormal distributions
        if len(self.abnormal_distributions) > 0:
            combined_data = np.vstack(
                (self.raw_distributions, self.abnormal_distributions)
            ).T
        else:
            combined_data = self.raw_distributions.T

        # Calculate percentiles
        self.reference_percentiles = np.nanpercentile(
            combined_data, self.percentiles, axis=1
        ).T  # (num_labels, num_percentiles)

        # Calculate normalization factors
        self.max_values = np.nanmax(combined_data, axis=1).reshape(-1, 1)
        self.min_values = np.nanmin(combined_data, axis=1).reshape(-1, 1)

        # Normalize reference percentiles
        self.reference_percentiles = (self.reference_percentiles - self.min_values) / (
            self.max_values - self.min_values + 1e-7
        )

    def optimize(
        self, population_size: int = 25, generations: int = 10
    ) -> Tuple[List[int], float]:
        """Optimize trace selection.

        Args:
            population_size: Size of the genetic algorithm population
            generations: Number of generations to evolve

        Returns:
            Tuple of (selected_indices, mse_score)
        """
        if not GEATPY_AVAILABLE:
            return self._fallback_optimization()

        logger.info(
            f"Starting sample optimization with GA (pop={population_size}, gen={generations})"
        )

        try:
            # Create optimization problem
            problem = self._create_geatpy_problem()

            # Create algorithm
            algorithm = ea.soea_DE_best_1_bin_templet(
                problem,
                ea.Population(Encoding="RI", NIND=population_size),
                MAXGEN=generations,
                logTras=0,
            )

            # Run optimization
            result = ea.optimize(
                algorithm,
                verbose=False,
                drawing=0,
                outputMsg=False,
                drawLog=False,
                saveFlag=False,
            )

            mse_score = result["ObjV"].flatten().tolist()[0]
            selected_indices = self._get_indices_from_variables(result["Vars"])

            logger.info(f"Sample optimization completed. MSE: {mse_score:.6f}")

            return selected_indices, mse_score

        except Exception as e:
            logger.error(f"Genetic algorithm optimization failed: {e}")
            return self._fallback_optimization()

    def _create_geatpy_problem(self):
        """Create Geatpy optimization problem."""

        # This would create a custom Geatpy problem similar to SampleProblem2
        # For now, return a simplified version
        class SimpleProblem(ea.Problem):
            def __init__(self, optimizer):
                self.optimizer = optimizer
                name = "SampleProblem"
                M = 1  # Single objective
                maxormins = [1]  # Minimize
                Dim = len(optimizer.quotas)
                varTypes = [1] * Dim  # Discrete variables
                lb = [0] * Dim
                ub = [optimizer.combination_count - 1] * Dim
                lbin = [1] * Dim
                ubin = [1] * Dim

                super().__init__(name, M, maxormins, Dim, varTypes, lb, ub, lbin, ubin)

            def evalVars(self, Vars):
                return self.optimizer._evaluate_combinations(Vars)

        return SimpleProblem(self)

    def _evaluate_combinations(self, variables: np.ndarray) -> np.ndarray:
        """Evaluate combination variables to compute MSE."""
        # Get selected combinations
        selected_combinations = self.all_combinations[
            variables, range(len(self.quotas))
        ]

        # Extract indices
        all_indices = []
        for row in selected_combinations:
            row_indices = []
            for combo in row:
                row_indices.extend(combo.indices.tolist())
            all_indices.append(row_indices)

        # Calculate MSE for each solution
        mse_scores = []
        for indices in all_indices:
            if not indices:
                mse_scores.append(float("inf"))
                continue

            sample_data = self.raw_distributions[indices, :]
            mse = self._calculate_distribution_mse(sample_data)
            mse_scores.append(mse)

        return np.array(mse_scores).reshape(-1, 1)

    def _calculate_distribution_mse(self, sample_data: np.ndarray) -> float:
        """Calculate MSE between sample and reference distributions."""
        if len(sample_data) == 0:
            return float("inf")

        # Add abnormal data if available
        if len(self.abnormal_distributions) > 0:
            sample_data = np.vstack((sample_data, self.abnormal_distributions))

        # Calculate sample percentiles
        sample_percentiles = np.nanpercentile(sample_data.T, self.percentiles, axis=1).T

        # Normalize sample percentiles
        sample_percentiles = (sample_percentiles - self.min_values) / (
            self.max_values - self.min_values + 1e-7
        )

        # Calculate MSE
        mse = np.mean((sample_percentiles - self.reference_percentiles) ** 2)

        return mse

    def _get_indices_from_variables(self, variables: np.ndarray) -> List[int]:
        """Extract trace indices from optimization variables."""
        if variables.shape[0] == 0:
            return []

        # Take first solution
        solution = variables[0] if len(variables.shape) > 1 else variables

        selected_combinations = self.all_combinations[solution, range(len(self.quotas))]

        all_indices = []
        for combo in selected_combinations:
            all_indices.extend(combo.indices.tolist())

        return all_indices

    def _fallback_optimization(self) -> Tuple[List[int], float]:
        """Fallback optimization when Geatpy is not available."""
        logger.info("Using fallback random sampling optimization")

        best_indices = []
        best_mse = float("inf")

        # Try random combinations
        for _ in range(100):  # Try 100 random combinations
            indices = []
            for i, quota in enumerate(self.quotas):
                if quota > 0:
                    start = sum(self.base_counts[:i])
                    end = start + self.base_counts[i]
                    if quota <= (end - start):
                        selected = random.sample(range(start, end), quota)
                        indices.extend(selected)

            if indices:
                sample_data = self.raw_distributions[indices, :]
                mse = self._calculate_distribution_mse(sample_data)

                if mse < best_mse:
                    best_mse = mse
                    best_indices = indices

        logger.info(f"Fallback optimization completed. MSE: {best_mse:.6f}")
        return best_indices, best_mse
