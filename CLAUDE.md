# Volatility Trading Bot - Claude Instructions

## Project Overview
This is a volatility trading bot that trades credit spreads on major ETFs when volatility spikes occur. The bot uses Claude AI for trade analysis and decision making.

## 📚 Strategy Documentation
- **Current Strategy**: Basic volatility spike trading (being phased out)
- **New Professional Strategy**: See [docs/PROFESSIONAL_STRATEGY.md](docs/PROFESSIONAL_STRATEGY.md)
- **Migration Plan**: See [docs/MIGRATION_PLAN.md](docs/MIGRATION_PLAN.md)

## Key Components
1. **Main Trading Bot** (`src/core/volatility_bot.py`) - Live trading engine
2. **Backtesting System** (`src/backtest/`) - Historical performance testing
3. **Dashboards** - Streamlit UIs for monitoring and analysis
   - Main Dashboard: http://localhost:8501
   - Backtest Dashboard: http://localhost:8502

## Important Configuration
- **Claude Model**: Use `claude-sonnet-4-20250514` for all API calls
- **Rate Limiting**: Claude API is limited to 5 requests/minute. Backtest engine uses 4/minute to be safe.
- **Test Commands**: Always run tests when making changes

## Testing Commands
```bash
# Verify system components
python3 scripts/verify_system.py

# Test backtesting with progress
python3 scripts/tests/test_backtest_with_progress.py

# Verify backtest fixes
python3 scripts/tests/verify_backtest_fixes.py
```

## Dashboard Launch Commands
```bash
# Main trading dashboard
python3 -m streamlit run src/ui/dashboard.py --server.port 8501

# Backtesting dashboard
python3 -m streamlit run src/ui/backtest_dashboard.py --server.port 8502
```

## Recent Fixes
1. Fixed Claude model name errors (was using incorrect model names)
2. Added rate limiting to backtest engine to prevent API errors
3. Fixed Streamlit duplicate element ID errors
4. Added progress indicators to backtest dashboard
5. Reduced volatility event frequency from 15% to 5% for faster testing

## Environment Variables Required
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ANTHROPIC_API_KEY`
- `ALPACA_BASE_URL` (use paper trading URL for testing)

## Development Notes
- Always test changes before committing
- Use paper trading for development
- Monitor API rate limits during testing
- Check dashboard logs for errors

## Claude Integration Requirements

### Current Claude Prompt (Being Phased Out)
- Simple volatility spike analysis
- Basic confidence scoring
- Fixed position sizing

### New Professional Claude Prompt (TradeBrain-V)
- See full prompt template in [docs/PROFESSIONAL_STRATEGY.md](docs/PROFESSIONAL_STRATEGY.md)
- Requires structured JSON input with:
  - Account balance
  - Current positions with Greeks
  - Universe data (price, IV rank, RSI, SMA, delta, skew)
  - Macro calendar events
  - Confidence model output
- Returns structured JSON with specific trade instructions
- Adheres to strict ruleset with no deviation

### Claude Requirements
- Model: `claude-sonnet-4-20250514`
- Rate limit: 5 requests/minute (use 4 to be safe)
- Always request reasoning in the output
- Log all Claude decisions for audit trail
- Implement retry logic for API failures