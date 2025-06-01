# Recent Changes Summary

## Codebase Reorganization (Latest)

### New Folder Structure
```
volatility-trading-bot/
├── src/
│   ├── core/           # Core trading logic
│   │   ├── trade_manager.py
│   │   ├── position_tracker.py
│   │   └── volatility_bot.py
│   ├── data/           # Data management
│   │   ├── trade_db.py
│   │   ├── simulated_pnl.py
│   │   └── database.py
│   └── ui/             # User interface
│       └── dashboard.py
├── tests/              # Test suite
├── docs/               # Documentation
├── deployment/         # Deployment configs
└── run_dashboard.py    # Main entry point
```

### Key Improvements

1. **P&L Calculation Fixes**
   - Fixed max loss calculation: now correctly uses (spread_width - credit_per_contract) * contracts * 100
   - Fixed P&L logic for credit spreads in simulated_pnl.py
   - Ensured losses cannot exceed maximum defined loss

2. **Test Suite**
   - Added comprehensive test suite in tests/ directory
   - Core functionality tests for database and P&L tracking
   - All tests passing for non-Alpaca dependent code

3. **Live Mode Preservation**
   - Live trading logic remains fully intact
   - When dev_mode=False, real Alpaca API calls are made
   - Options execution flow preserved in trade_manager.py

4. **Database Improvements**
   - SQLite database for persistent storage
   - Simulated P&L tracker now loads from database on initialization
   - Thread-safe database operations

## Running the Application

### Development Mode (Default)
```bash
python run_dashboard.py
```
- Uses simulated market data
- Claude analyzes simulated data but provides real decisions
- Trades are logged but not sent to broker
- P&L is simulated with realistic win/loss scenarios

### Live Mode
Set dev_mode=False in dashboard:
- Uses real Alpaca market data
- Real options chain fetching
- Actual trade execution via Alpaca API
- Real position tracking and P&L

## Testing
```bash
# Run simple functionality tests
python tests/test_simple.py

# Run core tests (no external dependencies)
python tests/test_core.py
```

## Important Notes

1. **Dev Mode**: Only market data is simulated. Claude AI analysis and all logic remains real.

2. **Live Mode Requirements**:
   - Alpaca API keys (paper or live)
   - Anthropic API key for Claude
   - Proper environment variables in .env file

3. **P&L Tracking**:
   - Dev mode: Simulated with 70% win rate
   - Live mode: Real P&L from Alpaca positions

4. **Options Execution**:
   - Dev mode: Full simulation of order flow
   - Live mode: Real orders sent to Alpaca