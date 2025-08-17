#!/usr/bin/env python3
"""
Test script for TracePicker with real data format.
This script tests TracePicker on real experiment data without creating synthetic data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracepicker.cli import app

if __name__ == "__main__":
    print("TracePicker - Real Data Testing")
    print("=" * 40)
    print("Usage examples:")
    print("  python test_real_data.py run /path/to/experiment/data --sample-rate 0.1")
    print("  python test_real_data.py info /path/to/experiment/data")
    print()
    print("Expected data structure:")
    print("  /path/to/experiment/data/")
    print("  ├── normal_traces.parquet")
    print("  ├── abnormal_traces.parquet")
    print("  ├── env.json (optional)")
    print("  └── ...")
    print()
    print("Or with subdirectory structure:")
    print("  /path/to/experiment/data/")
    print("  └── experiment-name/")
    print("      ├── normal_traces.parquet")
    print("      ├── abnormal_traces.parquet")
    print("      ├── env.json")
    print("      └── ...")
    print()

    # Run the CLI
    app()
