# Volatility Trading Bot

An automated options trading bot that uses Claude AI to identify and execute credit spread strategies during market volatility spikes.

## Features

- **Real-time Market Monitoring**: Continuously scans major ETFs (SPY, QQQ, IWM, DIA) for volatility events
- **AI-Powered Analysis**: Uses Claude Sonnet 4 to analyze market conditions and make trading decisions
- **Automated Execution**: Executes credit spreads through Alpaca Trading API
- **Risk Management**: Built-in position monitoring with profit targets and stop losses
- **Backtesting**: Comprehensive backtesting framework with real historical data
- **Dual Dashboard System**: 
  - Main trading dashboard for live monitoring and control
  - Separate backtesting dashboard for strategy analysis

## Quick Start

### Prerequisites

- Python 3.8+
- Alpaca Trading Account (paper or live)
- Anthropic API Key (for Claude AI)
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Hussein1147/volatility-trading-bot.git
cd volatility-trading-bot
```

2. Create and activate virtual environment:
```bash
python -m venv trading_bot_env
source trading_bot_env/bin/activate  # On Windows: trading_bot_env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.template .env
# Edit .env with your API keys
```

### Running the Bot

#### Main Trading Dashboard
```bash
python run_dashboard.py
# Access at http://localhost:8501
```

#### Backtesting Dashboard
```bash
python run_backtest.py
# Access at http://localhost:8502
```

## Project Structure

```
volatility-trading-bot/
├── src/
│   ├── core/           # Core trading logic
│   │   ├── trade_manager.py      # Trade execution and management
│   │   ├── volatility_bot.py     # Main bot logic
│   │   └── position_tracker.py   # Position monitoring
│   ├── data/           # Data management
│   │   ├── trade_db.py          # SQLite database interface
│   │   ├── simulated_pnl.py     # P&L tracking for dev mode
│   │   └── database.py          # PostgreSQL models (for deployment)
│   ├── ui/             # User interfaces
│   │   ├── dashboard.py         # Main trading dashboard
│   │   └── backtest_dashboard.py # Backtesting interface
│   └── backtest/       # Backtesting framework
│       ├── backtest_engine.py   # Core backtesting logic
│       ├── data_fetcher.py      # Historical data retrieval
│       └── visualizer.py        # Results visualization
├── scripts/            # Utility scripts
│   ├── verify_system.py         # System verification tool
│   └── tests/                   # Test scripts
├── tests/              # Unit tests
├── docs/               # Documentation
└── requirements.txt    # Python dependencies
```

## Trading Strategy

The bot implements a volatility-based credit spread strategy:

1. **Signal Detection**: Monitors for price moves > 1.5% with IV rank > 70
2. **Direction Analysis**: 
   - Big move DOWN → Sell CALL credit spreads
   - Big move UP → Sell PUT credit spreads
3. **Strike Selection**: 1.5-2 standard deviations from current price
4. **Expiration**: 14-30 DTE for optimal theta decay
5. **Risk Management**: 
   - Profit target: 35% of max profit
   - Stop loss: 100% of credit received
   - Time stop: Exit if < 7 DTE

## Configuration

### Bot Settings (via Dashboard)

- **Symbols**: ETFs to monitor
- **Min Price Move**: Minimum % move to trigger analysis (default: 1.5%)
- **Min IV Rank**: Minimum implied volatility rank (default: 70)
- **Confidence Threshold**: Claude's minimum confidence to trade (default: 70%)
- **Scan Interval**: Time between market scans (default: 300 seconds)

### Risk Parameters

- **Profit Target**: % of max profit to close (default: 35%)
- **Stop Loss**: % loss to exit (default: 100%)
- **Time Stop**: Days to expiration to close (default: 7)
- **Max Daily Loss**: Maximum allowed daily loss

## Development Mode

The bot includes a development mode for testing without real trades:

- Simulated market data generation
- Full trade execution flow without broker submission
- Realistic P&L tracking with time decay
- Same Claude AI analysis as live mode

Toggle via the dashboard checkbox.

## Backtesting

The backtesting framework allows you to test strategies on historical data:

- **Real Data**: Uses actual Alpaca stock prices
- **Options Data**: Real data from Feb 2024+, simulated for earlier dates
- **Performance Metrics**: Sharpe ratio, max drawdown, win rate, etc.
- **Visualization**: Equity curves, trade analysis, monthly returns

### Running a Backtest

1. Launch the backtesting dashboard
2. Configure parameters in the sidebar
3. Click "Run Backtest"
4. Analyze results across multiple tabs

## System Verification

Run the verification script to ensure everything is configured correctly:

```bash
python scripts/verify_system.py
```

This checks:
- API connectivity
- Database setup
- Dependencies
- Dashboard accessibility

## API Documentation

### Data Sources

- **Stock Data**: Alpaca Markets (real-time and historical)
- **Options Data**: Alpaca Markets (Feb 2024 onwards)
- **AI Analysis**: Anthropic Claude Sonnet 4

### Database

The bot uses SQLite for local storage with tables for:
- Trade history
- Claude analyses
- Market scans
- Bot logs

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for cloud deployment instructions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Disclaimer

This bot is for educational purposes. Trading options involves substantial risk of loss. Past performance does not guarantee future results. Always test thoroughly with paper trading before using real money.