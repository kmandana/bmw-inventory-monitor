#!/usr/bin/env python3
"""
BMW Pre-Owned Vehicle Search - Main Entry Point
Run this script to start the vehicle search
"""
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from main import main

if __name__ == '__main__':
    main()

