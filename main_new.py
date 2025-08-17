#!/usr/bin/env python3
"""
New main entry point for TracePicker with modern data format support.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracepicker.cli import app

if __name__ == "__main__":
    app()
