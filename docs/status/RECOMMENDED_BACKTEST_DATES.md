# 🎯 Recommended Backtest Date Ranges

## ⚠️ Important: Data Availability
- **Alpaca Options Data**: Only available from **February 2024 onwards**
- **Using dates before Feb 2024 will be SLOW** and use simulated data

## ✅ BEST Date Ranges for Quick Testing

### 1. **Recent Volatility (FASTEST)**
```
Start: 2024-10-01
End: 2024-11-01
Symbols: SPY
Min Price Move: 0.8%
Min IV Rank: 35
```
- Recent data, fast processing
- Some volatility around election period

### 2. **August 2024 Volatility**
```
Start: 2024-08-01
End: 2024-08-31
Symbols: SPY, QQQ
Min Price Move: 1.0%
Min IV Rank: 40
```
- Market pullback period
- Good volatility events

### 3. **Quick 1-Week Test**
```
Start: 2024-10-25
End: 2024-11-01
Symbols: SPY
Min Price Move: 0.5%
Min IV Rank: 30
```
- Very fast (2-3 minutes)
- Good for testing

## ❌ AVOID These Date Ranges

1. **Anything before February 2024** - No real options data
2. **Full year backtests** - Takes 30-60+ minutes
3. **Too many symbols** - Each symbol multiplies processing time

## 🚀 Pro Tips

1. **Start Small**: Test 1 week with 1 symbol first
2. **Then Expand**: Once working, try 1 month
3. **Monitor Progress**: Watch the activity log
4. **Be Patient**: Even 1 month takes 10-15 minutes

## 📊 Expected Timing

| Period | Symbols | Expected Time |
|--------|---------|---------------|
| 1 week | 1 | 2-3 minutes |
| 1 month | 1 | 10-15 minutes |
| 1 month | 3 | 20-30 minutes |
| 1 year | 1 | 45-60 minutes |
| 1 year | 4 | 2-3 hours |

Your backtest was trying to process **1 full year with 4 symbols** starting from a date with no options data - that's why it appeared stuck!