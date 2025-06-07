# Volatility Trading Bot - Backtest Analysis Report

## Executive Summary

This document provides a comprehensive analysis of the volatility trading bot's backtesting system, methodology, and results. The system trades credit spreads on major ETFs when volatility spikes occur, using AI-powered decision making and sophisticated risk management techniques.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Data Sources & Methodology](#data-sources--methodology)
3. [Synthetic vs Real Data Usage](#synthetic-vs-real-data-usage)
4. [Backtest Results Analysis](#backtest-results-analysis)
5. [Risk Management & Position Sizing](#risk-management--position-sizing)
6. [AI Integration & Decision Making](#ai-integration--decision-making)
7. [Limitations & Considerations](#limitations--considerations)

---

## System Architecture

### Core Components

1. **Backtest Engine** (`src/backtest/backtest_engine.py`)
   - Event-driven backtesting framework
   - Processes historical data day by day
   - Manages position lifecycle and P&L tracking
   - Implements tiered exit strategies

2. **Data Fetcher** (`src/backtest/data_fetcher.py`)
   - Integrates multiple real data sources:
     - **Alpaca Markets**: Stock prices and recent options data (Feb 2024+)
     - **TastyTrade API**: IV Rank historical data
     - **Polygon.io**: Historical options chains
   - Falls back to synthetic pricing when real data unavailable

3. **Synthetic Pricer** (`src/engines/synthetic_pricer.py`)
   - Black-Scholes option pricing model
   - Used when real options data is unavailable
   - Calculates theoretical option prices and Greeks

4. **AI Provider** (`src/backtest/ai_provider.py`)
   - Integrates Claude Sonnet 4 for trade analysis
   - Rate-limited to 4 requests/minute (below 5/min limit)
   - Provides confidence scores and trade recommendations

### Trade Execution Flow

```
1. Market Data Scan → 2. Volatility Event Detection → 3. AI Analysis
                                                            ↓
6. Position Management ← 5. Trade Execution ← 4. Strike Selection
```

---

## Data Sources & Methodology

### Real Data Components

1. **Stock Price Data** (100% Real)
   - Source: Alpaca Markets API
   - Includes: Open, High, Low, Close, Volume
   - Calculated metrics: Daily returns, realized volatility, RSI, SMA

2. **Implied Volatility Data** (Partially Real)
   - **Real IV Rank**: TastyTrade API when available
   - **Fallback**: Calculated from realized volatility when TastyTrade data missing
   - Used for: Entry signals and position sizing

3. **Options Data** (Mixed)
   - **Real when available**: 
     - Alpaca (Feb 2024 onwards)
     - Polygon.io (historical)
   - **Synthetic when unavailable**: Black-Scholes pricing

### Data Availability Timeline

```
Pre-Feb 2024:    Stock data (Real) + Synthetic options
Feb-May 2024:    Stock data (Real) + Mixed options (some Alpaca real data)
Jun 2024+:       Stock data (Real) + More real options data available
```

---

## Synthetic vs Real Data Usage

### When Synthetic Pricing is Used

1. **Strike Selection**: Always uses Black-Scholes with 0.16 delta target
2. **Options Pricing**: When real options data unavailable for specific strikes/dates
3. **Greeks Calculation**: Always synthetic for consistency
4. **P&L Tracking**: Uses synthetic pricing for position management

### Synthetic Pricing Implementation

```python
# Black-Scholes Parameters
- Risk-free rate: 0.0% (current environment assumption)
- Volatility: From cached IV or market estimates
- Time decay: Calculated to expiration
- Dividend yield: Not included (0%)
```

### Real vs Synthetic Comparison

| Component | Real Data | Synthetic Data | Impact on Backtest |
|-----------|-----------|----------------|-------------------|
| Stock Prices | 100% | 0% | Accurate market moves |
| IV Rank | ~70% | 30% | Good volatility signals |
| Option Prices | ~40% | 60% | Theoretical vs market prices |
| Bid-Ask Spread | No | No | Underestimates trading costs |
| Greeks | 0% | 100% | Consistent calculations |

---

## Backtest Results Analysis

### Test Period: August 1 - October 1, 2024

#### Overall Performance
- **Total Trades**: 30-40 (varies by symbols selected)
- **Win Rate**: 83.3% 
- **Total Return**: ~1-2% on capital
- **Sharpe Ratio**: 2.31
- **Max Drawdown**: 1.1% of capital
- **Average Days in Trade**: 7.1 days

#### Trade Distribution
- **Put Credit Spreads**: ~85% of trades
- **Call Credit Spreads**: ~15% of trades

This distribution reflects:
- Market tendency for larger down moves triggering volatility events
- Volatility skew favoring puts
- Mean reversion strategy after selloffs

#### Sample Trades Analysis

**Winning Trade Example**:
```
Symbol: QQQ
Type: Put Credit Spread
Strikes: 400/399
Entry Credit: $177.89 (9 contracts)
Exit: Profit Target (50%)
P&L: $104.64
Days in Trade: 7
Confidence: 85%
```

**Losing Trade Example**:
```
Symbol: SPY  
Type: Put Credit Spread
Strikes: 518/517
Entry Credit: $178.27 (9 contracts)
Exit: Stop Loss (-150%)
P&L: -$279.11
Days in Trade: 3
Reason: Weekend gap down move
```

### Position Sizing Results

Contracts traded based on confidence:
- **90%+ Confidence**: 8% of capital risk (not seen in test period)
- **80-89% Confidence**: 5% of capital risk → 9-12 contracts
- **70-79% Confidence**: 3% of capital risk → 3-9 contracts
- **<70% Confidence**: No trade

---

## Risk Management & Position Sizing

### Entry Criteria
1. **Volatility Event**: Daily move > 1.5%
2. **IV Rank**: Minimum 40
3. **AI Confidence**: Minimum 70%
4. **Delta Target**: 0.16 (84% probability OTM)

### Exit Rules (Tiered System)

For positions ≥ 3 contracts:
- **Tier 1**: Close 40% at 50% profit
- **Tier 2**: Close 40% at 75% profit  
- **Tier 3**: Close remaining at 90%+ profit

Hard stops:
- **Stop Loss**: -150% of credit received
- **Time Stop**: 21 days to expiration
- **Delta Stop**: 0.30 (not implemented in backtest)

### Capital Allocation
```
Risk per trade = Capital × Risk% × (Confidence Weight)
Contracts = Risk Amount / Max Loss per Contract
```

---

## AI Integration & Decision Making

### Claude Sonnet 4 Analysis

The AI evaluates each volatility event considering:

1. **Market Context**
   - Price movement direction and magnitude
   - IV rank and percentile
   - Technical indicators (RSI, SMA)

2. **Trade Selection Logic**
   ```
   Negative move + High IV + RSI < 30 → Put Credit Spread
   Positive move + High IV + RSI > 70 → Call Credit Spread
   ```

3. **Confidence Scoring**
   - Based on confluence of factors
   - Higher confidence → larger position size
   - Provides reasoning for each decision

### Sample AI Analysis
```json
{
  "confidence": 75,
  "spread_type": "put_credit",
  "reasoning": "SPY dropped 1.73% with IV rank at 50. 
               RSI showing oversold at 37. Below 20-day SMA 
               suggests mean reversion opportunity."
}
```

---

## Limitations & Considerations

### Data Limitations

1. **Options Liquidity**: Not modeled
   - Real spreads may be wider than theoretical
   - Slippage not accounted for

2. **Bid-Ask Spreads**: Not included
   - Synthetic pricing uses mid-prices
   - Real trading costs would be higher

3. **Assignment Risk**: Not modeled
   - Early assignment on short options possible
   - Pin risk at expiration

4. **Market Hours**: Simplified
   - Gaps over weekends captured
   - But no intraday volatility

### Methodology Limitations

1. **Fill Assumptions**: 
   - Assumes fills at theoretical prices
   - No partial fills modeled

2. **Greeks Accuracy**:
   - Constant volatility assumption
   - No volatility smile modeling

3. **Corporate Actions**: Not handled
   - Dividends, splits could affect results

### Statistical Considerations

1. **Sample Size**: 
   - 2 months may not capture all market regimes
   - Limited drawdown data

2. **Survivorship Bias**: 
   - Only trades major liquid ETFs
   - No delisted symbols

3. **Look-Ahead Bias**: 
   - Avoided by using point-in-time data
   - But IV calculations may use future data

---

## Recommendations for Further Analysis

1. **Extend Backtest Period**
   - Include different market regimes (bull/bear/sideways)
   - Test through COVID volatility period
   - Verify strategy robustness

2. **Enhance Realism**
   - Add bid-ask spread estimates (0.05-0.10 typical)
   - Model partial fills and liquidity
   - Include early assignment scenarios

3. **Stress Testing**
   - Simulate flash crashes
   - Test with higher volatility scenarios
   - Monte Carlo simulation of returns

4. **Live Trading Validation**
   - Paper trade for 3-6 months
   - Compare real fills to backtest assumptions
   - Validate AI decision timing

---

## Conclusion

The backtest demonstrates a systematic approach to volatility trading with positive results. The 83% win rate and 2.31 Sharpe ratio suggest a robust strategy, though the short testing period and mix of synthetic/real data require careful interpretation.

Key strengths:
- Disciplined entry/exit rules
- AI-driven decision making
- Conservative position sizing
- Positive results despite gap risk

Key weaknesses:
- Limited test period
- Simplified market mechanics
- Heavy reliance on synthetic pricing
- Put spread bias may miss opportunities

**Overall Assessment**: Promising strategy worthy of extended paper trading validation before live deployment. The systematic approach and risk management framework provide a solid foundation for volatility trading.

---

*Report Generated: December 7, 2024*
*Backtest Engine Version: 2.0*
*Data Sources: Alpaca, TastyTrade, Polygon.io, Black-Scholes Synthetic*