#!/usr/bin/env python3
"""
Launch script for the backtesting dashboard
"""

import sys
import os
import subprocess

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def main():
    """Run the backtesting Streamlit dashboard on a different port"""
    dashboard_path = os.path.join(project_root, "src", "ui", "backtest_dashboard.py")
    
    # Run on port 8502 to avoid conflict with main dashboard on 8501
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        dashboard_path,
        "--server.port", "8502",
        "--server.headless", "true"
    ])

if __name__ == "__main__":
    print("🚀 Starting Volatility Trading Bot Backtesting Dashboard...")
    print("📊 Dashboard will be available at http://localhost:8502")
    print("\nNote: The main trading dashboard runs on port 8501")
    print("      You can run both dashboards simultaneously\n")
    main()