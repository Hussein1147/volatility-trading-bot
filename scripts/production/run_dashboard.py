#!/usr/bin/env python3
"""
Main entry point for running the volatility trading bot dashboard
"""

import sys
import os
import subprocess

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def main():
    """Run the Streamlit dashboard"""
    dashboard_path = os.path.join(project_root, "src", "ui", "dashboard.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])

if __name__ == "__main__":
    main()