"""
SATTVA AI AGENT — CLI Runner
"""

import sys
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sattva.cli.app import main

if __name__ == "__main__":
    main()
