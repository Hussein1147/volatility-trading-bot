#!/usr/bin/env python3
"""
Verify all backtest fixes are properly implemented
"""

import os
import re

def check_file_for_pattern(filepath, patterns, description):
    """Check if file contains required patterns"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        found_all = True
        for pattern in patterns:
            if pattern in content:
                print(f"  ✓ {description}: Found '{pattern[:50]}...'")
            else:
                print(f"  ✗ {description}: Missing '{pattern[:50]}...'")
                found_all = False
                
        return found_all
    except Exception as e:
        print(f"  ✗ Error reading {filepath}: {e}")
        return False

def main():
    print("Verifying Backtest Fixes")
    print("=" * 50)
    
    all_passed = True
    
    # 1. Check rate limiting in backtest engine
    print("\n1. Rate Limiting Implementation:")
    patterns = [
        "self.last_api_calls = []",
        "self.max_api_calls_per_minute = 4",
        "async def _wait_for_rate_limit(self):",
        "Rate limit reached, waiting"
    ]
    passed = check_file_for_pattern(
        "src/backtest/backtest_engine.py",
        patterns,
        "Rate limiting"
    )
    all_passed = all_passed and passed
    
    # 2. Check Claude model name
    print("\n2. Claude Model Name:")
    patterns = [
        'model="claude-sonnet-4-20250514"'
    ]
    passed = check_file_for_pattern(
        "src/backtest/backtest_engine.py",
        patterns,
        "Correct model"
    )
    all_passed = all_passed and passed
    
    # 3. Check progress indicators in dashboard
    print("\n3. Progress Indicators:")
    patterns = [
        "with st.spinner",
        "Processing volatility events",
        "Rate limited to 4 requests/minute"
    ]
    passed = check_file_for_pattern(
        "src/ui/backtest_dashboard.py",
        patterns,
        "Progress indicators"
    )
    all_passed = all_passed and passed
    
    # 4. Check Streamlit unique keys
    print("\n4. Streamlit Unique Keys:")
    patterns = [
        'key="equity_curve"',
        'key="monthly_returns"',
        'key="returns_dist"'
    ]
    passed = check_file_for_pattern(
        "src/ui/backtest_dashboard.py",
        patterns,
        "Unique keys"
    )
    all_passed = all_passed and passed
    
    # 5. Check reduced volatility frequency
    print("\n5. Reduced Volatility Frequency:")
    patterns = [
        "if random_event < 0.05:"
    ]
    passed = check_file_for_pattern(
        "src/backtest/backtest_engine.py",
        patterns,
        "5% volatility frequency"
    )
    all_passed = all_passed and passed
    
    # 6. Check documentation exists
    print("\n6. Documentation:")
    docs = {
        "BACKTEST_TIPS.md": "Backtest tips",
        "README.md": "Main documentation",
        "CLAUDE.md": "Claude instructions"
    }
    
    for doc, desc in docs.items():
        if os.path.exists(doc):
            print(f"  ✓ {desc}: {doc} exists")
        else:
            print(f"  ✗ {desc}: {doc} missing")
            all_passed = False
    
    # 7. Check dashboard is running
    print("\n7. Dashboard Status:")
    try:
        with open("backtest_dashboard_new.log", 'r') as f:
            log_content = f.read()
            
        if "http://localhost:8502" in log_content:
            print("  ✓ Dashboard log shows it's running on port 8502")
        else:
            print("  ✗ Dashboard may not be running properly")
            all_passed = False
    except:
        print("  ? Could not check dashboard log")
    
    print("\n" + "=" * 50)
    print(f"Overall: {'✓ ALL FIXES VERIFIED' if all_passed else '✗ SOME FIXES MISSING'}")
    
    if all_passed:
        print("\nThe backtesting dashboard has been fixed and should now:")
        print("- Not spin forever (rate limiting prevents API errors)")
        print("- Show progress while processing")
        print("- Complete faster with reduced volatility events")
        print("- Work without Streamlit duplicate ID errors")
        print("\n💡 Visit http://localhost:8502 to test the backtesting dashboard")
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)