- Project Status: Volatility trading bot development in progress
- Dashboard Access: Local Streamlit dashboard, likely running on http://localhost:8501 
- Current Work: Set up initial trading bot infrastructure, implementing volatility trading strategies

## CRITICAL DASHBOARD TESTING REQUIREMENTS
⚠️ **ALWAYS RUN VERIFICATION TESTS** - Dashboard tests may pass but dashboard might not be accessible
1. Run `python test_dashboard.py` - ALL tests must pass including Live Verification
2. Run `python verify_dashboard.py` - MUST show HTTP 200 and Streamlit detected
3. Use `python launch_dashboard.py` for safe launching with validation
4. Check TESTING_PROCEDURES.md for complete testing protocol

## Dashboard Modernization Status
- UI has been modernized with professional dark theme matching Webull/Robinhood aesthetic
- Simplified 3-tab interface: Dashboard, Trades, Settings
- All bot functionality preserved with clean, maintainable code
- Testing suite ensures dashboard is actually live and accessible before claiming success

## Testing
- Dashboard tests: `python launch_dashboard.py` (includes verification)
- Trading tests: `python test_trading_comprehensive.py` (100% pass rate)
- All tests consolidated for simplicity
- Edge cases fully covered including flash crashes, circuit breakers, etc.
- See TESTING_GUIDE.md for complete documentation
- Remember to run all test before deploying dashboard
- always verify and test dashboard before launching

## Project Workflow
- Read all the readme before starting sessions
- IMPORTANT: Do not create new Python files unnecessarily, especially for volatility bot and dashboard files
- Always clean up after coding to maintain project organization and reduce clutter
- Make sure to always clean up temporary files after finishing development and clean up the code base

## Development Guidance
- Verify assumptions if you're not sure and ask me if necessary but don't be overly eager to ask. Use your better judgment to avoid mistakes
- Please remember to run all test before launching dashboard