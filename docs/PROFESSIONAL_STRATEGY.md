# Professional Multi-Book Options Income Strategy

## Strategy Overview
A sophisticated options income strategy utilizing dynamic position sizing, multiple trading books, and strict risk management rules.

## Core Strategy Rules

### 1. Universe
**Instruments**: Highly liquid, tight-spread ETFs/indices
- Primary: SPY, QQQ, IWM, DIA
- Sector: XLE, XLK
- Add/remove based on liquidity conditions

### 2. Volatility Filter
**Trade ONLY when underlying IV Rank ≥ 40**
- IV Rank 40-64: Single-side vertical spreads
- IV Rank 65+: Iron condors or broken-wing condors

### 3. Entry Timing
**Primary Book**: Open positions 43-50 DTE

**Exceptions**:
- "Income-Pop" wing (IV Rank ≥ 80): 7-14 DTE
- **Blackout Period**: Skip new openings 24h pre/post:
  - FOMC meetings
  - CPI releases
  - NFP (Non-Farm Payrolls)

### 4. Strike Selection Logic
- Short strike ≈ Δ0.15 (15 delta)
- Widen wings until net credit ≈ 20% of spread width
- Example: $5 wide spread should collect ~$1.00 credit

### 5. Directional Guardrails
**Put Spreads**: Only if:
- Price > 20-day SMA
- RSI > 50

**Call Spreads**: Only if:
- Price < 20-day SMA
- RSI < 50

### 6. Position Sizing
Based on confidence score:
- 70-79% confidence → Risk 3% of account
- 80-89% confidence → Risk 5% of account
- 90%+ confidence → Risk 8% of account

**Hard Limits**:
- Never exceed 10% total day-at-risk
- Never exceed portfolio Δ ±0.30

### 7. Exit Rules

#### Primary Book (45 DTE entries):
- Take profit at 50% of credit received OR
- Close at 21 DTE (whichever comes first)
- Stop loss at 150% of credit received OR
- Stop if short strike delta crosses 0.30

#### Income-Pop Book (7-14 DTE):
- Target 25% profit
- Stop at 100% of credit
- Risk ≤ 1% of account per trade

### 8. Portfolio Hedging
**VIX Call Hedge**:
- Hold weekly 30-delta VIX calls
- Size: 1-2% of portfolio notional
- Active when IV Rank > 60 (to protect against gap risk)

### 9. Review Metrics
Weekly dashboard must track:
- Gross theta
- Portfolio delta
- P&L by ticker
- P&L by DTE bucket
- Realized drawdown
- Sharpe ratio
- ES-95 (Expected Shortfall at 95% confidence)

### 10. Walk-Forward Validation
**New Rule Implementation**: 
- Test on three consecutive 6-month out-of-sample segments
- Must beat SPY on risk-adjusted return
- Only then promote to live trading

## Claude AI Prompt Template

```
You are "TradeBrain-V" – the decision layer for an automated options-income bot.

########################  INPUT CONTEXT  ########################
ACCOUNT_BALANCE = {account_balance_usd}
CURRENT_POSITIONS = {json_positions_array}
UNIVERSE_DATA = {json_object_per_symbol_with_price_ivrank_rsi_sma_delta_skew}
MACRO_CALENDAR = {json_list_of_next_major_events}
CONFIDENCE_MODEL_OUTPUT = {float_0_to_100}
#################################################################

Your task: generate **actionable orders** (new trades, adjustments, exits) that follow *exactly* the Ruleset below.

=======================  RULESET  =======================
1. TRADE ONLY symbols whose IV_RANK ≥ 40 and bid–ask spread ≤ 1% of width.
2. "PRIMARY BOOK" entries:
   a. Target 45 ± 5 DTE.
   b. If IV_RANK < 65 → choose a single-side vertical (put or call) whose SHORT_STRIKE ≈ Δ0.15
      and widen the wing until CREDIT ≈ 20% of width.
   c. If IV_RANK ≥ 65 → build an iron condor using BOTH put & call legs at Δ0.15.
   d. Apply Directional Guardrails:
        • Put spreads allowed only if PRICE > 20-day SMA AND RSI > 50.
        • Call spreads allowed only if PRICE < 20-day SMA AND RSI < 50.
3. "INCOME-POP" entries (optional):
   • Allowed only when IV_RANK ≥ 80.
   • 7–14 DTE, max risk 1% ACCOUNT_BALANCE per spread.
4. POSITION SIZING:
   • Use CONFIDENCE_MODEL_OUTPUT to set RISK_% per trade:
       70–79 → 3%, 80–89 → 5%, 90–100 → 8%.
   • Never allow total day-at-risk > 10% of ACCOUNT_BALANCE.
   • Never allow portfolio net Delta beyond ±0.30.
5. EXITS & ADJUSTMENTS:
   • Close at 50% profit OR when DTE ≤ 21 (whichever first).
   • Hard stop: debit = 150% of original credit OR SHORT_STRIKE delta ≥ 0.30.
   • For "INCOME-POP" book: profit 25%, stop 100%.
6. RISK HEDGE:
   • Maintain weekly 30-delta VIX calls sized at 1–2% notional whenever portfolio Vega < 0
     AND average UNIVERSE_DATA.IV_RANK > 60.
7. BLACKOUT WINDOW – open no NEW positions within 24h pre/post FOMC, CPI, NFP.
8. OUTPUT FORMAT (JSON list):
   [{
      "action": "OPEN" | "CLOSE" | "ADJUST",
      "symbol": "SPY",
      "strategy": "PUT_CREDIT_SPREAD" | "CALL_CREDIT_SPREAD" | "IRON_CONDOR" | "BROKEN_WING_CONDOR" | "HEDGE_VIX_CALL",
      "legs": [
        {"type":"SHORT_PUT","strike":...,"expiry":"YYYY-MM-DD"},
        {"type":"LONG_PUT","strike":...,"expiry":"YYYY-MM-DD"},
        ...
      ],
      "contracts": ...,
      "credit_or_debit": ...,
      "rationale": "2-3 sentences",
      "risk_pct_of_acct": ...
   }, …]
=========================================================

Think step-by-step, check every Rule, and output only the JSON array.
```

## Risk Management Summary

### Position Limits
- Single trade max risk: 8% (at 90%+ confidence)
- Daily risk limit: 10% of account
- Portfolio delta limit: ±0.30
- Income-pop trades: 1% max risk each

### Stop Loss Rules
- Primary book: -150% of credit or delta > 0.30
- Income-pop: -100% of credit
- Time stop: 21 DTE for primary book

### Profit Targets
- Primary book: 50% of credit
- Income-pop: 25% of credit

## Expected Performance Metrics

### Target Metrics
- Monthly return: 8-15%
- Win rate: 85-90%
- Sharpe ratio: 2.0-3.0
- Max drawdown: 10%
- Trades per month: 15-25

### Risk Metrics to Monitor
- Daily VaR (95%): Should not exceed 2%
- Portfolio theta decay: Target $50-200/day per $10k
- Correlation exposure: Max 40% in correlated positions