"""Input schema and configuration definitions for TracePicker algorithm."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..entities.trace import Trace


@dataclass
class TracingConfig:
    """Configuration for the TracePicker algorithm."""

    # Buffer configuration
    buffer_size: int = 4000
    pool_height: int = 1000

    # Sampling configuration
    sample_rate: float = 0.1
    combination_count: int = 100

    # Quota allocation parameters
    np_quota: int = 1000
    ng_quota: int = 50

    # Group subset selection parameters
    np_sample: int = 25
    ng_sample: int = 10

    # Random seed for reproducibility
    seed: int = 1

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.buffer_size <= 0:
            raise ValueError("buffer_size must be positive")
        if not 0 < self.sample_rate <= 1:
            raise ValueError("sample_rate must be between 0 and 1")
        if self.combination_count < 2:
            raise ValueError("combination_count must be at least 2")


@dataclass
class TracingInput:
    """Input data structure for the TracePicker algorithm."""

    traces: List[Trace]
    config: TracingConfig
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate input after initialization."""
        if not self.traces:
            raise ValueError("traces list cannot be empty")

        if not all(isinstance(trace, Trace) for trace in self.traces):
            raise TypeError("All elements in traces must be Trace instances")

        self.config.validate()

    @property
    def trace_count(self) -> int:
        """Get the total number of traces."""
        return len(self.traces)

    @property
    def trace_ids(self) -> List[str]:
        """Get all trace IDs."""
        return [trace.trace_id for trace in self.traces]


@dataclass
class TracingResult:
    """Result structure from the TracePicker algorithm."""

    # Sampled trace IDs
    sampled_trace_ids: List[str]

    # Performance metrics
    encoding_time: float
    sampling_time: float
    other_time: float

    # Processing statistics
    total_traces: int
    sampled_traces: int
    abnormal_traces: int

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None

    @property
    def total_time(self) -> float:
        """Get total processing time."""
        return self.encoding_time + self.sampling_time + self.other_time

    @property
    def sampling_ratio(self) -> float:
        """Get actual sampling ratio."""
        return self.sampled_traces / self.total_traces if self.total_traces > 0 else 0.0
