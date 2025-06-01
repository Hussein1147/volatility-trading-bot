#!/usr/bin/env python3
"""
Main entry point for running the volatility trading bot dashboard
"""

import sys
import os
import subprocess

# Add the current directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run the Streamlit dashboard"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "src", "ui", "dashboard.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])

if __name__ == "__main__":
    main()