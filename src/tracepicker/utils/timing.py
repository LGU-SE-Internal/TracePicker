"""Time measurement utilities for performance profiling."""

import time
from functools import wraps
from typing import Any, Callable, Tuple

from rcabench_platform.v2.logging import logger


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time.

    Args:
        func: Function to be timed

    Returns:
        Wrapped function that logs execution time
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result

    return wrapper


def measure_time(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """Measure execution time of a function call.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Tuple of (result, execution_time)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time = end_time - start_time
    return result, execution_time


class TimeTracker:
    """Context manager for tracking execution time."""

    def __init__(self, operation_name: str = "operation"):
        """Initialize time tracker.

        Args:
            operation_name: Name of the operation being tracked
        """
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None

    def __enter__(self) -> "TimeTracker":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End timing and log result."""
        self.end_time = time.time()
        if exc_type is None:
            logger.info(
                f"{self.operation_name} completed in {self.elapsed_time:.4f} seconds"
            )
        else:
            logger.error(
                f"{self.operation_name} failed after {self.elapsed_time:.4f} seconds"
            )

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time if self.end_time is not None else time.time()
        return end_time - self.start_time
