# Migration Quick Start Guide

## 🚀 Week 1 Actions (Start Immediately)

### Day 1-2: Data Infrastructure
```bash
# 1. Add technical indicators to data fetcher
# File: src/backtest/data_fetcher.py
# Add: calculate_sma(df, period=20)
# Add: calculate_rsi(df, period=14)

# 2. Expand universe
# File: src/core/volatility_bot.py
# Change: symbols = ['SPY', 'QQQ', 'IWM']
# To: symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLE', 'XLK']

# 3. Test new data feeds
python3 scripts/test_enhanced_data.py  # Create this
```

### Day 3-4: Database Updates
```sql
-- Run these schema updates
sqlite3 trade_history.db < sql/migration_schema.sql

-- Verify with:
sqlite3 trade_history.db ".schema trades"
```

### Day 5: Create Parallel Testing
```python
# Create: src/core/strategy_comparison.py
# Run both strategies side-by-side
# Log differences for analysis
```

## 📋 Pre-Migration Checklist

### Data Readiness
- [ ] RSI calculation working
- [ ] SMA calculation working
- [ ] Greeks data available from Alpaca
- [ ] VIX data feed active
- [ ] Economic calendar API integrated

### Code Readiness
- [ ] Delta-based strike selection implemented
- [ ] Directional filters (RSI + SMA) working
- [ ] Dynamic position sizing ready
- [ ] Multi-book structure created

### Testing Readiness
- [ ] Backtesting updated with new rules
- [ ] Paper trading account ready
- [ ] Monitoring dashboard updated
- [ ] Alert system configured

## 🔄 Daily Migration Tasks

### Week 1
- **Monday**: Set up technical indicators
- **Tuesday**: Add Greeks calculations
- **Wednesday**: Implement directional filters
- **Thursday**: Update position sizing logic
- **Friday**: Run first backtest comparison

### Week 2
- **Monday**: Implement multi-book structure
- **Tuesday**: Add IV-based strategy selection
- **Wednesday**: Create exit management system
- **Thursday**: Test with paper trading
- **Friday**: Review and adjust

## 📊 Key Files to Modify

### Core Strategy Files
1. `src/core/volatility_bot.py`
   - Lower IV threshold to 40
   - Add directional filters
   - Implement multi-book logic

2. `src/core/trade_manager.py`
   - Add delta-based strike selection
   - Dynamic position sizing
   - Enhanced exit rules

3. `src/backtest/backtest_engine.py`
   - Update for new strategy rules
   - Add Greeks tracking
   - Multi-book support

### New Files to Create
1. `src/core/professional_strategy.py`
   - Main strategy orchestrator
   - Implements all new rules

2. `src/core/greeks_manager.py`
   - Portfolio Greeks tracking
   - Delta limits enforcement

3. `src/core/vix_hedge_manager.py`
   - VIX hedge automation
   - Hedge sizing logic

## 🎯 Quick Win Implementation

Before full migration, implement these for immediate improvement:

### 1. Lower IV Threshold (1 hour)
```python
# In src/core/volatility_bot.py
# Change: self.min_iv_rank = 70
# To: self.min_iv_rank = 40
```

### 2. Add Directional Filter (2 hours)
```python
# Add to analyze_opportunity():
if symbol_rsi > 50 and price > sma_20:
    # Only put spreads allowed
elif symbol_rsi < 50 and price < sma_20:
    # Only call spreads allowed
else:
    return None  # No trade
```

### 3. Dynamic Position Sizing (2 hours)
```python
# Replace fixed contracts with:
def size_position(confidence):
    if 70 <= confidence < 80:
        risk_pct = 0.03
    elif 80 <= confidence < 90:
        risk_pct = 0.05
    elif confidence >= 90:
        risk_pct = 0.08
    
    return calculate_contracts(risk_pct)
```

## 🚨 Emergency Procedures

### If Something Breaks
1. **Immediate**: `touch /tmp/KILL_SWITCH` (implement kill switch check)
2. **Revert**: `git checkout main -- src/core/volatility_bot.py`
3. **Restart**: `supervisorctl restart trading_bot`

### Rollback Commands
```bash
# Full rollback
./scripts/rollback_strategy.sh

# Partial rollback (keep data changes)
./scripts/rollback_strategy.sh --keep-data
```

## 📈 Success Metrics Week 1

You're on track if:
- [ ] Technical indicators calculating correctly
- [ ] Backtest shows 3x more trades with new IV threshold
- [ ] Directional filters reducing bad trades by 30%+
- [ ] No system errors in paper trading

## 🔗 Related Documentation
- [Full Strategy Rules](PROFESSIONAL_STRATEGY.md)
- [Detailed Migration Plan](MIGRATION_PLAN.md)
- [Current System Status](../SYSTEM_STATUS.md)

## 💬 Support
- Slack: #trading-bot-migration
- Email: trading-bot-support@company.com
- Emergency: Call lead developer

Remember: **Test Everything Twice!**