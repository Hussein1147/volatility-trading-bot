# Trading Workflow

## Overview

The volatility trading bot follows this workflow:

```
Market Scan → Claude Analysis → Trade Decision → Execution → Monitoring
```

## Detailed Workflow

### 1. Market Scanning
- **Dev Mode**: Generates simulated market data with realistic price movements
- **Live Mode**: Fetches real market data from Alpaca API
- Scans configured symbols (SPY, QQQ, IWM, DIA, etc.)
- Checks for volatility spikes based on:
  - Minimum price move (default: 1.5%)
  - Minimum IV rank (default: 70)

### 2. Claude Analysis
When a volatility spike is detected:
- Sends market data to Claude AI
- Claude analyzes based on trading rules:
  - If stock moves DOWN >1.5% → Consider CALL credit spread
  - If stock moves UP >1.5% → Consider PUT credit spread
  - IV Rank must be >70 for good premiums
- Claude returns:
  - Trade decision (should_trade: true/false)
  - Spread type and strike prices
  - Confidence level (0-100)
  - Reasoning for the decision

### 3. Trade Execution

#### Dev Mode (Simulated)
- Logs the trade details
- Stores in SQLite database
- No actual orders sent to Alpaca

#### Live Mode (Real Trading)
- If confidence >= threshold (default: 70%):
  1. Fetches real options chain from Alpaca
  2. Finds matching contracts for strikes
  3. Validates credit is positive
  4. Submits orders:
     - SELL order for short strike (collect premium)
     - BUY order for long strike (protection)
  5. Records trade in database
  6. Starts position monitoring

### 4. Position Tracking

The system tracks positions in multiple ways:

1. **Real-time from Alpaca** (Live Mode):
   - `PositionTracker` class queries Alpaca API
   - Gets current positions, P&L, and account info
   - Groups options into spread positions

2. **Database Storage**:
   - All analyses stored in `claude_analyses` table
   - Executed trades in `trades` table
   - Activity logs in `bot_logs` table

3. **Dashboard Display**:
   - **Dashboard Tab**: Portfolio overview and activity log
   - **Trading Activity Tab**: 
     - All Activity: Shows all Claude analyses
     - Executed Trades Only: Shows only trades that were executed
     - Active Positions: Real positions from Alpaca (Live mode only)
   - **Settings Tab**: Configure bot parameters

## Trade Management

### Risk Controls
- Maximum daily loss limit
- Position size limits (2% of account)
- Stop loss at 75% of credit received
- Profit target at 35% of credit received
- Time-based exit (close at 3 DTE)

### Monitoring
- Continuous monitoring of active positions
- Automatic exit on stop loss or profit target
- P&L tracking and reporting

## Mode Differences

### Dev Mode
- Uses simulated market data
- Claude analyzes dummy data but provides real decisions
- Trades are simulated (not sent to Alpaca)
- No real positions or P&L

### Paper Trading Mode
- Uses real market data from Alpaca
- Claude analyzes real market conditions
- Trades executed in Alpaca paper account
- Real positions and P&L (paper money)

### Live Trading Mode
- Same as paper but with real money
- Uses production API keys
- Real financial risk

## Configuration

Key settings in dashboard:
- **Symbols**: Which stocks to monitor
- **Min Price Move %**: Minimum volatility threshold
- **Min IV Rank**: Minimum implied volatility rank
- **Scan Interval**: How often to check markets
- **Min Confidence %**: Claude's minimum confidence to trade

## Database Schema

- `claude_analyses`: All market analyses and decisions
- `trades`: Executed trades with details
- `bot_logs`: Activity and error logs
- `market_scans`: Market scan snapshots

The SQLite database (`trade_history.db`) persists all data for analysis and backtesting.