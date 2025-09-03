# TracePicker
python ./main.py sample batch -s tracepicker -d rcabench_sampler --rate 0.1 --rate 0.05 --mode online --clear --no-skip-finished
python ./main.py sample batch -s tracepicker -d rcabench_sampler_filtered --rate 0.001 --rate 0.005 --rate 0.01 --rate 0.05 --rate 0.1 --mode offline --mode o --clear --no-skip-finished
TracePicker is an intelligent trace sampling framework for distributed systems that uses machine learning and optimization techniques to select representative traces while maintaining statistical properties of the original trace distribution.

> **🚀 NEW**: TracePicker now supports modern parquet-based data formats and includes a modern CLI interface. See [README_NEW.md](README_NEW.md) for the latest features!

## Features

- **Intelligent Sampling**: Uses path encoding and anomaly detection for smart trace selection
- **Performance Optimization**: Implements genetic algorithms for optimal trace combination selection
- **Anomaly Detection**: Automatically identifies and prioritizes abnormal traces
- **Configurable**: Flexible configuration options for different use cases
- **Scalable**: Efficient buffer management and processing pipeline
- **🆕 Modern Data Formats**: Full support for parquet files with Polars integration
- **🆕 CLI Interface**: User-friendly command-line interface with rich output
- **🆕 Platform Integration**: Compatible with rcabench platform standards

## 🚀 Quick Start

### Modern Interface (Recommended)

```bash
# Run with new parquet data format
python tracepicker_cli.py run /path/to/experiment/data --sample-rate 0.1

# Show dataset information  
python tracepicker_cli.py info /path/to/experiment/data

# Test CLI interface
python benchmark.py --help
```

### Legacy Interface

```bash
# Traditional pickle format (legacy)
python eval.py --dataset A --data_dir data
```

For complete new features documentation, see **[README_NEW.md](README_NEW.md)**

## Architecture

The TracePicker framework consists of several key components:

### 1. Preprocessing (`src/tracepicker/preprocessing/`)
- **Data Validation**: Ensures trace data integrity and consistency
- **Normalization**: Standardizes trace format and attributes
- **Input Schema**: Defines structured input data format

### 2. Core Algorithm (`src/tracepicker/core/`)
- **TracePicker**: Main algorithm orchestrating the sampling process
- **Buffer Management**: Efficient storage and organization of traces
- **Path Encoding**: BFS-based tree encoding for trace path signatures
- **Historical Pool**: Tracks operation latency statistics

### 3. Optimization (`src/tracepicker/algorithms/`)
- **Quota Allocation**: Dynamic programming solution for optimal quota distribution
- **Sample Optimization**: Genetic algorithm for trace selection optimization
- **Input Schema**: Structured configuration and result formats
- **🆕 Platform Adapter**: Integration with rcabench platform

### 4. Utilities (`src/tracepicker/utils/`)
- **I/O Operations**: Pickle-based data loading and saving
- **🆕 New Data Loader**: Polars-based parquet file processing
- **🆕 Legacy Loader**: Backward compatibility for old formats
- **Timing**: Performance measurement and profiling tools

## Installation

```bash
# Install from source
git clone <repository-url>
cd TracePicker
pip install -e .

# Or install with optimization dependencies
pip install -e ".[optimization]"
```

## Usage

### Basic Usage

```python
from tracepicker import TracePicker, TracingConfig
from tracepicker.preprocessing import preprocess_raw_data
from tracepicker.utils.io_utils import load_pickle

# Load your trace data
traces = load_pickle("data/traces.pkl")

# Configure the algorithm
config = TracingConfig(
    buffer_size=4000,
    sample_rate=0.1,
    pool_height=1000,
    combination_count=100,
    seed=42
)

# Preprocess traces
tracing_input = preprocess_raw_data(traces, config)

# Run TracePicker
picker = TracePicker(config)
result = picker.process_traces(tracing_input)

# Access results
print(f"Sampled {result.sampled_traces} out of {result.total_traces} traces")
print(f"Sampling ratio: {result.sampling_ratio:.3f}")
print(f"Processing time: {result.total_time:.2f}s")
```

### Command Line Interface

```bash
# Run with default settings
python eval.py --dataset A --data_dir data

# Customize parameters
python eval.py \
    --dataset socialNetwork \
    --data_dir /path/to/data \
    --output_dir /path/to/output \
    --sample_rate 0.15 \
    --buffer_size 5000 \
    --seed 123
```

## Configuration

### TracingConfig Parameters

- `buffer_size`: Number of traces to buffer before sampling (default: 4000)
- `pool_height`: Maximum samples per operation label in historical pool (default: 1000)
- `sample_rate`: Fraction of traces to sample (0-1, default: 0.1)
- `combination_count`: Number of combinations for optimization (default: 100)
- `seed`: Random seed for reproducibility (default: 1)

### Advanced Configuration

```python
config = TracingConfig(
    buffer_size=8000,          # Larger buffer for better optimization
    sample_rate=0.05,          # Lower sampling rate
    pool_height=2000,          # More historical data
    combination_count=200,     # More optimization combinations
    np_quota=1000,            # Population size for quota allocation
    ng_quota=50,              # Generations for quota allocation
    np_sample=25,             # Population size for sample optimization
    ng_sample=10,             # Generations for sample optimization
    seed=42
)
```

## Algorithm Overview

### 1. Trace Encoding
Each trace is encoded using a BFS traversal of its span tree, creating a unique path signature that captures the service call structure.

### 2. Anomaly Detection
Traces are classified as abnormal based on:
- Error status codes
- Performance degradation (actual duration vs. expected duration)

### 3. Buffer Management
Traces are buffered and grouped by their path signatures until the buffer is full or processing is complete.

### 4. Quota Allocation
A dynamic programming algorithm optimally distributes sampling quotas among different path types to minimize variance.

### 5. Sample Optimization
A genetic algorithm selects the optimal combination of traces that best preserves the statistical properties of the original distribution.

## Output

TracePicker generates two main output files:

1. **Sample Results** (`{dataset}-TracePicker-sample.csv`):
   - `traceId`: Unique trace identifier
   - `decision`: Boolean indicating if trace was sampled

2. **Performance Metrics** (`{dataset}-TracePicker-cost.csv`):
   - `encode_t`: Time spent on trace encoding
   - `sample_t`: Time spent on sampling decisions
   - `other_t`: Time spent on other operations
   - `total_t`: Total processing time

## Performance

TracePicker is designed for efficiency:
- **Memory**: O(buffer_size) memory usage through buffering
- **Time**: Linear in number of traces for encoding, polynomial for optimization
- **Scalability**: Processes traces in batches for constant memory usage

## Dependencies

Core dependencies:
- `numpy>=1.21.0`: Numerical computations
- `pandas>=1.3.0`: Data manipulation
- `treelib>=1.6.0`: Tree data structures

Optional dependencies:
- `geatpy>=2.7.0`: Genetic algorithm optimization (recommended)
- `rcabench_platform[v2]`: Logging framework

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use TracePicker in your research, please cite:

```bibtex
@software{tracepicker2024,
  title={TracePicker: Intelligent Trace Sampling for Distributed Systems},
  author={TracePicker Team},
  year={2024},
  url={https://github.com/example/tracepicker}
}
```
