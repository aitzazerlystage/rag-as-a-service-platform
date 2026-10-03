#!/usr/bin/env python3
"""
Simple launcher script for PDF Chat Assistant Frontend
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from start_frontend import main

if __name__ == "__main__":
    main()
