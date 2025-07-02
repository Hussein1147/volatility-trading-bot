#!/usr/bin/env python3
"""
Test GitHub Actions locally to diagnose issues
"""
import os
import sys
import subprocess

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'ALPACA_API_KEY',
        'ALPACA_SECRET_KEY',
        'POLYGON_API_KEY',
        'GEMINI_API_KEY',
        'ANTHROPIC_API_KEY'
    ]
    
    print("=== Environment Check ===")
    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var}: Set")
        else:
            print(f"✗ {var}: Missing")
            missing.append(var)
    
    return len(missing) == 0

def check_dependencies():
    """Check if all dependencies can be imported"""
    print("\n=== Dependency Check ===")
    try:
        import pandas
        print("✓ pandas")
    except ImportError as e:
        print(f"✗ pandas: {e}")
        
    try:
        import yfinance
        print("✓ yfinance")
    except ImportError as e:
        print(f"✗ yfinance: {e}")
        
    try:
        import alpaca_trade_api
        print("✓ alpaca_trade_api")
    except ImportError as e:
        print(f"✗ alpaca_trade_api: {e}")
    
    return True

def test_scripts():
    """Test if the scripts can be imported"""
    print("\n=== Script Import Check ===")
    
    scripts = [
        'scripts/daily_iv_collector.py',
        'scripts/cron/collect_iv_intraday.py'
    ]
    
    for script in scripts:
        try:
            # Try to run with --help or import check
            result = subprocess.run(
                [sys.executable, script, '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 or 'usage' in result.stdout.lower():
                print(f"✓ {script}: OK")
            else:
                print(f"✗ {script}: {result.stderr[:100]}")
        except Exception as e:
            print(f"✗ {script}: {str(e)[:100]}")

def test_database():
    """Test database access"""
    print("\n=== Database Check ===")
    
    if os.path.exists('historical_iv.db'):
        print("✓ historical_iv.db exists")
        
        import sqlite3
        try:
            conn = sqlite3.connect('historical_iv.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM historical_iv")
            count = cursor.fetchone()[0]
            print(f"✓ Database accessible, {count} records")
            conn.close()
        except Exception as e:
            print(f"✗ Database error: {e}")
    else:
        print("✗ historical_iv.db not found")

if __name__ == "__main__":
    print("Testing GitHub Actions setup locally...\n")
    
    env_ok = check_environment()
    deps_ok = check_dependencies()
    test_scripts()
    test_database()
    
    if not env_ok:
        print("\n⚠️  Missing environment variables. Make sure to set them in GitHub Secrets.")
    
    print("\nRun this script to diagnose issues before pushing to GitHub Actions.")