"""I/O utilities for loading and saving data."""

import pickle
from typing import Any

from rcabench_platform.v2.logging import logger


def load_pickle(file_path: str) -> Any:
    """Load data from a pickle file.

    Args:
        file_path: Path to the pickle file

    Returns:
        Loaded data

    Raises:
        FileNotFoundError: If file doesn't exist
        pickle.PickleError: If file cannot be unpickled
    """
    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        logger.info(f"Successfully loaded data from {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except pickle.PickleError as e:
        logger.error(f"Failed to unpickle file {file_path}: {e}")
        raise


def save_pickle(file_path: str, data: Any) -> None:
    """Save data to a pickle file.

    Args:
        file_path: Path where to save the pickle file
        data: Data to be saved

    Raises:
        pickle.PickleError: If data cannot be pickled
        IOError: If file cannot be written
    """
    try:
        with open(file_path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Successfully saved data to {file_path}")
    except pickle.PickleError as e:
        logger.error(f"Failed to pickle data for {file_path}: {e}")
        raise
    except IOError as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise
