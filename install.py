"""
SATTVA AI AGENT — 1-Click Global CLI Installer.
Run: `python install.py` to register `sattva` as a system-wide command.
"""

import sys
import os
from pathlib import Path

# Add package root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sattva.cli.installer import run_global_installer

if __name__ == "__main__":
    run_global_installer()
