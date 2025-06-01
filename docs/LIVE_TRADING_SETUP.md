# Live Trading Setup Guide

## Current Status

### ✅ What's Ready:
1. **Market Data Integration** - Alpaca API for real-time stock data
2. **Claude Sonnet 4 Integration** - For market analysis
3. **Risk Management** - Stop loss, profit targets, daily loss limits
4. **Trade Monitoring** - Automated position monitoring
5. **Dev/Live Mode Toggle** - Easy switching between modes

### ❌ What's Missing:
1. **API Keys** - Need to be set in `.env` file
2. **Options Broker Integration** - Alpaca doesn't support options yet
3. **Trade Execution** - Currently stubbed out

## Setup Steps for Live Trading

### 1. Create `.env` file
```bash
# In project root directory
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here
ANTHROPIC_API_KEY=your_claude_api_key_here
ALPACA_PAPER_TRADING=true  # Set to false for real money
```

### 2. Options Trading Issue
**Important**: Alpaca currently doesn't support options trading. You have three choices:

#### Option A: Use TD Ameritrade API
- Supports options trading
- Requires updating `execute_trade_from_analysis` method
- Need TD Ameritrade developer account

#### Option B: Use Interactive Brokers (IBKR)
- Professional options trading platform
- More complex API but very powerful
- Requires IBKR account and API setup

#### Option C: Manual Execution
- Bot generates signals
- You manually execute trades
- Safest for testing initially

### 3. Implement Trade Execution
The `execute_trade_from_analysis` method in `dashboard.py` needs to be implemented based on your broker choice.

### 4. Testing Checklist
- [ ] Test with paper trading account first
- [ ] Start with single contract positions
- [ ] Monitor for at least 1 week in paper mode
- [ ] Verify all safety features work (stop loss, etc.)
- [ ] Test emergency stop procedures

### 5. Live Trading Settings
For real trading, use conservative settings:
```
Min Price Move: 1.5-2.0%
Min IV Rank: 70+
Min Confidence: 70+
Max Daily Loss: $500-1000
Stop Loss: 75%
Profit Target: 35-50%
```

## Safety Features

### Emergency Stop
To stop all trading immediately:
1. Click "Stop Bot" in dashboard
2. Or kill the process: `pkill -f streamlit`

### Position Limits
- Set `max_contracts` in settings
- Set `max_daily_loss` to limit risk

### Monitoring
- Check dashboard every few hours
- Review Claude Analysis tab for decisions
- Monitor open positions in Trades tab

## Broker Integration Examples

### TD Ameritrade (tda-api)
```python
# Install: pip install tda-api
from tda import auth, client
# Implementation details...
```

### Interactive Brokers (ib_insync)
```python
# Install: pip install ib_insync
from ib_insync import *
# Implementation details...
```

## Testing Protocol

1. **Paper Trading (2 weeks minimum)**
   - Run with live data but fake money
   - Verify all features work correctly
   - Track performance metrics

2. **Small Position Testing (1 month)**
   - Start with 1 contract positions
   - Gradually increase if profitable

3. **Full Trading**
   - Only after consistent paper profits
   - Keep position sizes reasonable
   - Always use stop losses

## Important Notes

1. **Options Risk**: Options can expire worthless. Never risk more than you can afford to lose.

2. **API Costs**: 
   - Alpaca: Free for market data
   - Claude API: ~$0.003 per analysis
   - Options data: May require paid subscription

3. **Tax Implications**: Options trading has complex tax rules. Consult a tax professional.

4. **Regulatory**: Ensure you meet pattern day trader requirements if applicable.

## Support

For issues:
1. Check logs in Activity Log
2. Review Claude Analysis for reasoning
3. Verify API keys are correct
4. Check broker connectivity

Remember: Start small, test thoroughly, and never trade with money you can't afford to lose!