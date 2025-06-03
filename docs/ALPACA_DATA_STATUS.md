# Alpaca Data Status

## Overview
The backtesting system is configured to use real Alpaca options data when available.

## API Configuration
- **Keys Used**: `ALPACA_API_KEY_PAPER_TRADING` and `ALPACA_SECRET_KEY_PAPER_TRADING`
- **Options Trading Level**: 3 (Full access)
- **Account Type**: Paper Trading

## Data Availability

### Stock Data
- **Available**: 5+ years of historical daily bars
- **Symbols**: All major ETFs and stocks (SPY, QQQ, IWM, etc.)
- **Data Points**: Open, High, Low, Close, Volume

### Options Data
- **Available From**: February 2024 onwards (per Alpaca documentation)
- **Before Feb 2024**: System uses sophisticated Black-Scholes simulation
- **Data Points**: 
  - Real-time bid/ask quotes with sizes
  - Strike prices and expirations
  - Open interest
  - Contract symbols

## Verification Scripts
Located in `scripts/data_verification/`:
- `test_alpaca_auth.py` - Verify API authentication
- `test_alpaca_options_data.py` - Fetch and save options data
- `check_alpaca_data_availability.py` - Check historical data ranges
- `verify_backtest_data.py` - Confirm backtest uses real data

## Test Results
Test outputs saved in `data/test_outputs/`:
- `alpaca_options_data_dump.txt` - Sample options chain data
- `backtest_test_results.txt` - Backtest verification results

## How Backtest Uses Data

1. **Recent Dates (after Feb 2024)**:
   - Fetches real options contracts from Alpaca
   - Gets real-time bid/ask quotes
   - Uses actual open interest and volume

2. **Historical Dates (before Feb 2024)**:
   - Uses `_simulate_options_chain()` method
   - Generates realistic options based on Black-Scholes
   - Maintains proper bid/ask spreads and Greeks

## Verification
Run this command to verify data access:
```bash
source trading_bot_env/bin/activate
python scripts/data_verification/test_alpaca_auth.py
```