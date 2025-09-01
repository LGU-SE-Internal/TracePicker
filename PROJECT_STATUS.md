# TracePicker Project Status

## ✅ Cleanup Complete + Sampler Integration + OFFLINE Mode (September 2, 2025)

### 🗂️ Final Project Structure
```
TracePicker/
├── src/tracepicker/           # Main package
│   ├── __init__.py           # Clean API exports + samplers
│   ├── algorithms/           # Core algorithms
│   │   ├── platform_adapter.py    # TracePickerAdapter, run_tracepicker
│   │   ├── input_schema.py        # Data structures
│   │   └── quota_problem_dp.py    # Optimization
│   ├── core/                # Core engine
│   │   ├── tracepicker.py   # Main TracePicker class
│   │   ├── bfs_encoder.py   # Path encoding
│   │   ├── buffer.py        # Buffer management
│   │   └── pool.py          # Historical pool
│   ├── entities/            # Data models
│   │   └── trace.py         # Trace and Span classes
│   ├── preprocessing/       # Data preprocessing
│   │   └── __init__.py      # Preprocessing functions
│   ├── samplers/            # 🆕 rcabench v2 samplers
│   │   ├── __init__.py      # Sampler exports
│   │   └── tracepicker_sampler.py # TraceSampler implementation
│   └── utils/               # Utilities
│       ├── data_loader.py   # Polars-based loading
│       ├── result_saver.py  # TraStrainer-style saving
│       ├── io_util.py       # I/O operations
│       └── *.py             # Other utilities
├── tracepicker_cli.py       # CLI entry point
├── benchmark.py             # Testing/benchmarking
├── eval.py                  # Legacy evaluation
├── test_offline_mode.py     # 🆕 OFFLINE mode testing
├── register_samplers.py     # 🆕 Auto-register samplers
├── SAMPLER_GUIDE.md        # 🆕 Sampler usage guide
└── README.md               # Updated documentation
```

### 🏗️ Architecture Components

#### Core API
- **TracePicker**: Main algorithm class
- **TracePickerAdapter**: Platform integration
- **run_tracepicker**: Main function entry point
- **TracepickerResultSaver**: Result saving with statistics

#### 🆕 rcabench v2 Samplers
- **TracePickerSampler**: Unified sampler supporting both ONLINE and OFFLINE modes
- **ONLINE Mode**: Traditional TracePicker batch processing
- **OFFLINE Mode**: Early termination with backfill strategy
- **register_samplers**: Auto-registration for rcabench platform

#### Data Pipeline
- **data_loader.py**: Modern Polars-based loading
- **result_saver.py**: Comprehensive result saving
- **Trace/Span**: Data models

#### CLI Interface
- **tracepicker_cli.py**: Main CLI entry
- **cli.py**: Typer-based interface with rich output

### 🔧 Key Improvements

1. **Clean Naming**: 
   - `main_new.py` → `tracepicker_cli.py`
   - `new_data_loader.py` → `data_loader.py`
   - `TracesAdapter` → `TracePickerAdapter`
   - `tracepicker_algorithm` → `run_tracepicker`

2. **Removed Legacy**:
   - Old `main.py`, demo files
   - `TracePicker/` directory
   - All backup and temporary files

3. **Modern Features**:
   - Polars integration for performance
   - TraStrainer-style statistics
   - Rich CLI with progress bars
   - Comprehensive result saving
   - 🆕 rcabench v2 TraceSampler interface
   - 🆕 ONLINE and OFFLINE sampling modes
   - 🆕 Early termination with smart backfill
   - 🆕 Cross-batch state preservation
   - 🆕 Auto-registration system

### ✅ Validation Status

- [x] All imports work correctly
- [x] CLI interface functional
- [x] No legacy references remaining
- [x] Documentation updated
- [x] Clean package structure
- [x] 🆕 rcabench v2 sampler interface
- [x] 🆕 ONLINE and OFFLINE mode implementation
- [x] 🆕 Early termination and backfill strategy
- [x] 🆕 Cross-batch state preservation
- [x] 🆕 Auto-registration system

### 🚀 Usage Examples

```bash
# CLI usage
python tracepicker_cli.py run /path/to/data --sample-rate 0.1
python tracepicker_cli.py info /path/to/data

# Python API
from tracepicker import run_tracepicker
result = run_tracepicker(data_folder="/path/to/data", sample_rate=0.1)

# 🆕 rcabench v2 Sampler
import tracepicker.register_samplers  # Auto-register
from rcabench_platform.v2.samplers.spec import global_sampler_registry
registry = global_sampler_registry()

# ONLINE mode (traditional)
sampler = registry["tracepicker"](buffer_size=4000, seed=42)

# OFFLINE mode (early termination + backfill)
# When target sampling rate is reached, processing stops early
# If final batch doesn't reach target, backfill from previous batches

# Benchmarking
python benchmark.py

# Test OFFLINE mode
python test_offline_mode.py
```

### 📦 Dependencies
- Core: polars, typer, rich, rcabench_platform
- Optional: geatpy for optimization

### 🚨 Features

- ✅ ONLINE sampling mode: Traditional TracePicker batch processing
- ✅ OFFLINE sampling mode: Early termination when target rate reached
  - Smart backfill from previous batches if target not met
  - Cross-batch state preservation for path statistics
  - Intelligent quota management across batches
- ✅ Automatic sampler registration for rcabench platform

**Status**: Production Ready ✅ + rcabench v2 Compatible ✅ + OFFLINE Mode ✅
