# TracePicker - Modern Version

TracePicker is now fully adapted for modern distributed tracing data formats and integrated with the rcabench platform.

## 🚀 Quick Start

### New CLI Interface (Recommended)

```bash
# Run TracePicker on real experiment data
python main_new.py run /path/to/experiment/data --sample-rate 0.1 --buffer-size 4000

# Show dataset information
python main_new.py info /path/to/experiment/data

# Run with custom parameters
python main_new.py run /path/to/experiment/data \
    --sample-rate 0.15 \
    --buffer-size 5000 \
    --combinations 200 \
    --seed 42 \
    --verbose
```

### Legacy CLI Interface

```bash
# Still works with old pickle format
python main.py --dataset A --data_dir TracePicker/data
```

### Test CLI with Help

```bash
# Get usage information and test CLI
python test_real_data.py --help
```

## 📊 New Data Format Support

TracePicker now supports modern parquet-based data formats with the following schema:

### Traces Schema

| Column | Type | Description |
|--------|------|-------------|
| time | datetime | Start time of a span in UTC |
| trace_id | string | Unique identifier of a trace |
| span_id | string | Unique identifier of a span |
| parent_span_id | string | Identifier of the parent span |
| service_name | string | Name of the service that generated the span |
| span_name | string | Name of the operation represented by the span |
| duration | uint64 | Duration of a span in nanoseconds |
| attr.* | * | Other attributes of a span |

Required files in data folder:
- `normal_traces.parquet` - Normal trace data
- `abnormal_traces.parquet` - Anomalous trace data
- `env.json` - Environment configuration (optional)

## 🔧 Integration with rcabench Platform

### Algorithm Class

```python
from tracepicker import TracePickerAlgorithm

# Use as rcabench algorithm
algorithm = TracePickerAlgorithm()
```

### Direct Function Call

```python
from tracepicker import tracepicker_algorithm
from pathlib import Path

result = tracepicker_algorithm(
    data_folder=Path("/path/to/data"),
    sample_rate=0.1,
    buffer_size=4000,
    seed=42
)
```

## 📦 Installation

### Dependencies

```toml
# pyproject.toml
dependencies = [
    "polars>=0.20.0",
    "typer[all]>=0.9.0", 
    "rich>=13.0.0",
    "rcabench-platform>=0.3.26",
    # ... other dependencies
]
```

### Install in Development Mode

```bash
pip install -e .
```

## 🏗️ Architecture Updates

### New Components

1. **Data Loader** (`src/tracepicker/utils/new_data_loader.py`)
   - Polars-based data loading
   - Automatic format conversion
   - Performance optimizations

2. **Platform Adapter** (`src/tracepicker/algorithms/platform_adapter.py`)
   - rcabench platform integration
   - Algorithm interface compliance
   - Standardized input/output formats

3. **Modern CLI** (`src/tracepicker/cli.py`)
   - Typer-based command line interface
   - Rich console output with progress bars
   - Interactive dataset information

4. **Legacy Compatibility** (`src/tracepicker/utils/legacy_loader.py`)
   - Backward compatibility with old pickle files
   - Automatic format migration
   - Module aliasing for seamless loading

### Updated Core Components

- **TracePicker Algorithm**: Enhanced with better error handling and logging
- **Preprocessing**: Improved validation and normalization
- **Entity Classes**: Extended with new data format support

## 📈 Performance Improvements

- **Polars Integration**: 10-100x faster data loading compared to pandas
- **Lazy Evaluation**: Memory-efficient processing of large datasets  
- **Optimized Encoding**: Improved BFS tree encoding performance
- **Parallel Processing**: Better utilization of multi-core systems

## 🔄 Migration Guide

### From Legacy Format

Your old pickle-based data will still work:

```python
# Old way (still works)
python main.py --dataset A --data_dir TracePicker/data

# New way (recommended for new data)
python main_new.py run /path/to/parquet/data
```

### From Legacy Code

```python
# Old way
from main import main
main()

# New way - direct algorithm
from tracepicker import tracepicker_algorithm
result = tracepicker_algorithm(data_folder=Path("data"))

# New way - CLI
from tracepicker.cli import app
app()

# New way - platform integration
from tracepicker import TracePickerAlgorithm
algorithm = TracePickerAlgorithm()
```

## 🧪 Testing

### Test with Real Data

```bash
# Test CLI with real experiment data
python test_real_data.py run /path/to/experiment/data --sample-rate 0.2 --verbose

# Check data info
python test_real_data.py info /path/to/experiment/data
```

### Unit Tests

```bash
pytest tests/
```

### CLI Testing

```bash
# Test info command
python main_new.py info /path/to/experiment/data

# Test run command  
python main_new.py run /path/to/experiment/data --sample-rate 0.2 --verbose
```

## 📋 Configuration Options

All previous configuration options are supported, plus new ones:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `buffer_size` | int | 4000 | Buffer size for trace processing |
| `sample_rate` | float | 0.1 | Sampling rate (0-1) |
| `pool_height` | int | 1000 | Pool height for encoder |
| `combination_count` | int | 100 | Number of combinations for optimization |
| `seed` | int | 42 | Random seed for reproducibility |

## 🔍 Output Format

### CLI Output

```bash
TracePicker Results
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric            ┃ Value     ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Total Traces      │ 1000      │
│ Sampled Traces    │ 150       │
│ Sampling Ratio    │ 0.150     │
│ Abnormal Traces   │ 25        │
│ Processing Time   │ 2.345s    │
└───────────────────┴───────────┘
```

### File Outputs

- `{dataset}_tracepicker_results.json` - Complete results
- `{dataset}_sampled_traces.csv` - Sampled trace IDs
- `{dataset}_summary.csv` - Summary statistics

## 🚨 Breaking Changes

1. **CLI Interface**: New typer-based CLI (old CLI still available)
2. **Data Format**: Primary support for parquet files (pickle still supported)
3. **Dependencies**: Added polars, typer, rich
4. **Output Format**: Enhanced JSON/CSV outputs

## 🤝 Contributing

The new architecture makes it easier to contribute:

1. **Data Loaders**: Add support for new data formats
2. **Algorithms**: Implement new sampling strategies
3. **CLI Features**: Add new commands and options
4. **Platform Integration**: Extend rcabench compatibility

## 📄 License

MIT License - see LICENSE file for details.
