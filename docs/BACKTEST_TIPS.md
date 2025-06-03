# Backtesting Tips

## Quick Start Settings (Fast Test)

For a quick test that completes in 1-2 minutes:
- **Date Range**: Last 30 days
- **Symbols**: 1-2 symbols (e.g., just SPY)
- **Min Price Move**: 2.5% (finds fewer opportunities)
- **Min IV Rank**: 80 (more selective)

## Full Backtest Settings (Comprehensive)

For a thorough analysis (5-10 minutes):
- **Date Range**: 6-12 months
- **Symbols**: All 4 ETFs (SPY, QQQ, IWM, DIA)
- **Min Price Move**: 1.5% (default)
- **Min IV Rank**: 70 (default)

## Understanding the Process

When you click "Run Backtest", the system:

1. **Scans Historical Data**: Looks for days with volatility spikes
2. **Analyzes with Claude AI**: Each opportunity is analyzed (rate limited to 4/minute)
3. **Simulates Trades**: Executes and manages positions
4. **Tracks Performance**: Monitors P&L and exit conditions

## Why It Takes Time

- **API Rate Limits**: Claude AI has a 5 requests/minute limit
- **Realistic Simulation**: Each trade is fully simulated with time decay
- **Comprehensive Analysis**: Every opportunity gets AI analysis

## Optimization Tips

1. **Start Small**: Test with 30 days first
2. **Increase Thresholds**: Higher min_price_move = fewer trades = faster
3. **Single Symbol**: Test one symbol at a time initially
4. **Off-Peak Hours**: Run longer backtests when not actively trading

## Expected Results

- **Volatility Events**: ~5-10 per month per symbol (market dependent)
- **Trade Signals**: ~30-50% of events become trades
- **Win Rate**: Typically 60-80% for credit spreads
- **Average Trade Duration**: 5-15 days

## Troubleshooting

If backtest seems stuck:
1. Check the progress indicators - it's likely just processing
2. Look at the dashboard log for any errors
3. Try a shorter date range or single symbol
4. Ensure your API keys are valid

Remember: Quality analysis takes time. The rate limiting ensures accurate results without overwhelming the API.