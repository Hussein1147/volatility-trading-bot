# Dashboard Testing & Launch Procedures

## ⚠️ CRITICAL FOR FUTURE MODEL INSTANCES ⚠️
**ALWAYS RUN VERIFICATION TESTS** - Even if tests pass, the dashboard might not be accessible. The test suite now includes live verification that actually confirms the dashboard is running and accessible in a browser.

## Overview
This document contains mandatory procedures for testing and launching the Volatility Trading Bot dashboard. **ALL TESTS MUST PASS** before the dashboard can be launched, including the live verification test that confirms browser accessibility.

## Quick Start

### For Future Model Instances
```bash
# 1. Navigate to project directory
cd /Users/djibrilkeita/Desktop/volatility-trading-bot

# 2. Activate virtual environment
source trading_bot_env/bin/activate

# 3. Run safe launcher (tests + launch)
python launch_dashboard.py
```

## Manual Testing Process

### 1. Environment Validation
```bash
# Check virtual environment
which python
# Should show: .../trading_bot_env/bin/python

# Test basic imports
python -c "import streamlit, pandas, plotly; print('✓ Core dependencies OK')"
```

### 2. Run Test Suite
```bash
# Run comprehensive test suite
python test_dashboard.py

# Expected output: "🟢 ALL TESTS PASSED - Dashboard ready for launch!"
# MUST see: "✓ PASS: Live verification - Dashboard confirmed live at http://localhost:8502"
```

### 3. Verify Dashboard is ACTUALLY Accessible
```bash
# Run verification script (ALWAYS DO THIS)
python verify_dashboard.py

# Should output:
# ✅ Dashboard is running on port 8501
# ✅ HTTP Status: 200
# ✅ Streamlit app detected
```

### 4. Launch Only If Tests Pass
```bash
# Option A: Use safe launcher (recommended)
python launch_dashboard.py

# Option B: Manual launch (only if tests passed)
streamlit run consolidated_dashboard.py --server.port 8501
```

## Test Suite Components

### Core Tests (Must Pass)
1. **Import Test** - All required modules load successfully
2. **Environment Test** - Virtual environment and files present
3. **Syntax Test** - Dashboard code compiles without errors
4. **Streamlit Test** - Streamlit installation functional
5. **Startup Test** - Dashboard starts without crashing
6. **Accessibility Test** - Dashboard responds to HTTP requests
7. **Content Test** - Expected UI elements present
8. **Error Test** - No critical runtime errors
9. **Live Verification Test** - Dashboard is ACTUALLY accessible in browser
   - Verifies HTTP 200 response
   - Checks content length > 100 bytes
   - Confirms Tornado server is running
   - Attempts to open in default browser
   - **THIS IS THE MOST IMPORTANT TEST**

### Test Files
- `test_dashboard.py` - Comprehensive test suite
- `launch_dashboard.py` - Safe launcher with validation

## Troubleshooting Common Issues

### Import Errors
```bash
# Fix: Install missing dependencies
pip install -r requirements.txt
```

### Environment Issues
```bash
# Fix: Ensure virtual environment is active
source trading_bot_env/bin/activate
which python  # Should show trading_bot_env path
```

### Port Conflicts
```bash
# Fix: Kill existing processes
lsof -i :8501
kill <PID>
```

### Dashboard Crashes
```bash
# Debug: Check for syntax errors
python -m py_compile consolidated_dashboard.py

# Debug: Test imports manually
python -c "from consolidated_dashboard import *"
```

## Dashboard Validation Checklist

### Pre-Launch (Required)
- [ ] Virtual environment activated
- [ ] All test suite components pass
- [ ] No critical errors in logs
- [ ] Required files present (dashboard, trade_manager, .env)

### Post-Launch (Verification)
- [ ] Dashboard loads at http://localhost:8501
- [ ] All tabs render correctly (Dashboard, Trades, Settings)
- [ ] Control buttons functional (Start/Stop Bot)
- [ ] No console errors visible
- [ ] UI styling applied correctly

## Error Resolution

### Session State Errors
**Symptom**: `st.session_state has no attribute 'xyz'`
**Fix**: Initialize session state variables before use

### Threading Errors
**Symptom**: Background threads fail to access session state
**Fix**: Pass parameters to thread functions instead of accessing session state

### Import Errors
**Symptom**: `ModuleNotFoundError` or `ImportError`
**Fix**: Check virtual environment and install requirements

### Streamlit Not Found
**Symptom**: `command not found: streamlit`
**Fix**: Activate virtual environment and reinstall streamlit

## File Structure Requirements

```
volatility-trading-bot/
├── consolidated_dashboard.py      # Main dashboard file
├── enhanced_trade_manager.py      # Trade management logic
├── test_dashboard.py             # Test suite
├── launch_dashboard.py           # Safe launcher
├── requirements.txt              # Dependencies
├── .env                         # Environment variables
├── trading_bot_env/             # Virtual environment
└── TESTING_PROCEDURES.md        # This file
```

## Security Notes

- Never commit API keys to repository
- Always use environment variables for sensitive data
- Test with dummy data before live trading
- Validate all user inputs in dashboard

## Performance Guidelines

- Dashboard should load within 10 seconds
- UI should be responsive with < 2 second interactions
- Memory usage should remain stable during operation
- No memory leaks in background threads

## Contact & Support

For issues with testing procedures:
1. Check logs in console output
2. Review error messages from test suite
3. Validate environment setup
4. Check file permissions and paths

---

**IMPORTANT**: Never launch the dashboard without passing the complete test suite. This prevents broken deployments and ensures user experience quality.