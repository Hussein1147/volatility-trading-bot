# AI Trade Analysis Flow - What Trades Go to the Model?

## Overview
The backtesting engine filters market data and only sends potential trade opportunities to the AI (Claude or Gemini) for analysis. Not every day or price movement gets analyzed - only those meeting specific criteria.

## Trade Selection Process

### 1. **Market Scanning** (_process_trading_day)
The backtest engine scans each trading day for all symbols in the watchlist (e.g., SPY, QQQ, IWM)

### 2. **Initial Filters** (_get_historical_data)
For each symbol, the system checks:
- **Minimum Price Move**: >= 1.5% daily change (configurable)
- **Market Data Available**: Stock must have valid price/volume data
- **Volatility Event**: Significant price movement indicating elevated volatility

```python
# Only return data for significant moves
if abs(percent_change) >= self.config.min_price_move:
    # This is a potential volatility event worth analyzing
```

### 3. **Pre-AI Filtering** (_analyze_opportunity)
Before sending to AI, additional checks:
- **IV Rank Threshold**: >= 40 (minimum for premium selling)
- **Data Quality**: Must have technical indicators (SMA, RSI)

Only if ALL conditions are met, the trade goes to AI analysis.

### 4. **What Data Goes to AI**
When a trade opportunity passes all filters, the AI receives:

```
## Current Market Data
Symbol: SPY
Current Price: $450.00
Today's Move: -2.5%  (volatility event!)
Volume: 100,000,000
IV Rank: 75.0 (high volatility)
IV Percentile: 80.0

## Technical Indicators
20-day SMA: $445.00
14-day RSI: 55.0
Price Position: Above SMA

## Account Information
Account Balance: $100,000
Open Positions: 2
Current Portfolio Delta: -15.00
Max Risk per Trade: 2%

## Strike Selection Guidance
For 0.15 delta targeting at current price $450.00:
- PUT spreads: Short strike approximately 405-405
- CALL spreads: Short strike approximately 495-518
```

### 5. **AI Decision Making**
The AI (Claude/Gemini) then:
1. Applies the TradeBrain-V professional rules
2. Checks directional filters (price vs SMA, RSI levels)
3. Evaluates if conditions are suitable for credit spreads
4. Calculates confidence score based on multiple factors
5. Recommends specific strategy (put spread, call spread, iron condor)
6. Suggests position sizing based on confidence

### 6. **Post-AI Execution**
If AI recommends a trade (should_trade = true):
- System executes with recommended parameters
- Uses AI's confidence score for position sizing
- Applies professional exit rules

## Example Flow

Day 1: SPY moves +0.5% → **Ignored** (below 1.5% threshold)
Day 2: SPY moves -2.5%, IV Rank 75 → **Sent to AI** → AI recommends iron condor
Day 3: QQQ moves +3%, IV Rank 35 → **Ignored** (IV rank too low)
Day 4: IWM moves -2%, IV Rank 45 → **Sent to AI** → AI recommends call credit spread

## Summary

The AI only analyzes **high-quality volatility events** that meet:
- Significant price movement (volatility spike)
- Sufficient IV rank for premium selling
- Complete market data for analysis

This ensures the AI focuses on the best opportunities rather than analyzing every minor market movement. In a typical month, this might be 5-10 trade opportunities out of ~20 trading days.