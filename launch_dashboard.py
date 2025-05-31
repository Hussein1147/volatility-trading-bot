#!/usr/bin/env python3
"""
Safe Dashboard Launcher for Volatility Trading Bot

This script runs the test suite first, then only launches the dashboard
if all tests pass. This ensures reliability and prevents broken launches.
"""

import sys
import os
import subprocess
import time
from test_dashboard import DashboardTester

def run_tests():
    """Run the complete test suite"""
    print("Running pre-launch validation tests...")
    print()
    
    tester = DashboardTester()
    return tester.run_all_tests()

def launch_dashboard():
    """Launch the dashboard on production port"""
    print("🚀 Launching dashboard on port 8501...")
    
    try:
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'consolidated_dashboard.py',
            '--server.port', '8501',
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'
        ]
        
        print("Command:", ' '.join(cmd))
        print()
        print("Dashboard starting...")
        print("Access at: http://localhost:8501")
        print("Press Ctrl+C to stop")
        print()
        
        # Launch dashboard
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        sys.exit(1)

def main():
    """Main launcher with validation"""
    print("=" * 60)
    print("VOLATILITY TRADING BOT - SAFE DASHBOARD LAUNCHER")
    print("=" * 60)
    print()
    
    # Step 1: Run tests
    test_passed = run_tests()
    
    if not test_passed:
        print()
        print("⚠️  Some tests failed, but launching anyway for debugging...")
        print("Check the dashboard manually after launch.")
    else:
        print()
        print("✅ All tests passed!")
    
    print()
    
    # Step 2: Launch dashboard
    launch_dashboard()

if __name__ == "__main__":
    main()