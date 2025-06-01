# Volatility Trading Bot

An automated volatility trading bot that uses Alpaca's API and Claude AI for analyzing market conditions and executing credit spread strategies.

## Strategy Overview

This bot implements a two-phase volatility trading strategy:

**Phase 1 - Volatility Spike**: When significant market moves occur (>1.5%), the bot:
- Sells call credit spreads on market drops
- Sells put credit spreads on market rallies
- Targets strikes 1.25-1.75 standard deviations from current price

**Phase 2 - Volatility Contraction**: After volatility spike settles:
- Adds butterfly spreads or opposite-side credit spreads
- Captures volatility mean reversion

## Features

- ✅ Real-time market scanning for SPY, QQQ, IWM, DIA
- ✅ IV rank/percentile calculation for volatility detection
- ✅ Claude AI integration for intelligent trade analysis
- ✅ Paper trading with Alpaca (commission-free)
- ✅ Automatic position monitoring and profit targets
- ✅ Risk management (2% max risk per trade)
- ✅ Two-phase strategy implementation

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Alpaca paper trading account (free at [alpaca.markets](https://alpaca.markets))
- Anthropic API key for Claude AI

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Hussein1147/volatility-trading-bot.git
cd volatility-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. API Setup

#### Alpaca Setup:
1. Go to [alpaca.markets](https://alpaca.markets) and create a free account
2. Navigate to "Paper Trading" in the dashboard
3. Generate API keys (API Key ID and Secret Key)
4. Note: Paper accounts automatically get Level 3 options approval

#### Claude API Setup:
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account and generate an API key
3. You'll get $5 free credits to start

### 4. Environment Configuration

```bash
# Copy the template
cp .env.template .env

# Edit .env with your API keys
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
```

### 5. Running the Bot

#### Run the Dashboard (Recommended):
```bash
python run_dashboard.py
```

This opens a Streamlit dashboard at http://localhost:8501 with:
- Real-time position monitoring
- P&L tracking
- Trade history
- Claude AI analysis logs

#### Run the Bot Directly:
```bash
python -m src.core.volatility_bot
```

The bot will:
- Verify your API connections
- Start monitoring market conditions during trading hours (9:30 AM - 4:00 PM ET)
- Log all analysis and trades to console
- Execute paper trades when opportunities are found

## Project Structure

```
volatility-trading-bot/
├── src/
│   ├── core/           # Core trading logic
│   │   ├── trade_manager.py      # Trade execution and management
│   │   ├── position_tracker.py   # Position monitoring
│   │   └── volatility_bot.py     # Main bot logic
│   ├── data/           # Data management
│   │   ├── trade_db.py          # Trade history database
│   │   ├── simulated_pnl.py     # P&L simulation for dev mode
│   │   └── database.py          # PostgreSQL models (optional)
│   └── ui/             # User interface
│       └── dashboard.py         # Streamlit dashboard
├── deployment/         # Deployment configurations
├── docs/              # Documentation
├── scripts/           # Utility scripts
├── requirements.txt   # Python dependencies
├── run_dashboard.py   # Dashboard entry point
└── README.md         # This file
```

## Trading Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Account Size | $10,000 | Simulated within paper account |
| Max Risk/Trade | 2% ($200) | Maximum loss per position |
| Profit Target | 35% | Percentage of max profit to close |
| Min Price Move | 1.5% | Threshold to trigger analysis |
| Min IV Rank | 70 | Minimum implied volatility rank |
| Symbols | SPY, QQQ, IWM, DIA | ETFs monitored |
| DTE Range | 7-45 days | Days to expiration target |

## Strategy Logic

### Entry Criteria
- Significant price move (≥1.5%) detected
- High IV rank (≥70) indicating elevated volatility
- Claude AI confirms trade setup with ≥70% confidence

### Position Sizing
- Calculate contracts based on $200 max risk
- Ensure adequate buying power available
- Account for spread width and premium received

### Exit Strategy
- Close at 35% of maximum profit potential
- Monitor positions every 5 minutes during market hours
- Implement stop-loss if unrealized loss exceeds threshold

## File Structure

```
volatility-trading-bot/
├── volatility_bot.py      # Main bot implementation
├── requirements.txt       # Python dependencies
├── .env.template         # Environment variables template
├── .gitignore           # Git ignore patterns
└── README.md            # This documentation
```

## Current Implementation Status

### ✅ Completed Features:
- Market data fetching and analysis
- IV rank/percentile calculation
- Claude AI integration for trade decisions
- Paper trading framework
- Position monitoring structure
- Risk management parameters

### 🚧 Development Roadmap:
- [ ] Real options chain data integration
- [ ] Actual options order execution (currently simulation)
- [ ] Options symbol formatting (OCC standard)
- [ ] Profit target automation
- [ ] Discord/email alert system
- [ ] Performance tracking dashboard
- [ ] Backtesting framework

## Risk Disclaimers

⚠️ **Important Risk Warnings:**

- This is educational software for learning algorithmic trading
- All trades are executed in paper trading mode only
- Past performance does not guarantee future results
- Options trading involves substantial risk of loss
- Never trade with money you cannot afford to lose
- Always paper trade strategies before using real money

## Troubleshooting

### Common Issues:

**"ModuleNotFoundError"**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

**"Invalid API credentials"**
- Verify API keys in .env file
- Ensure Alpaca keys are for paper trading
- Check that Claude API key is valid

**"No market data"**
- Bot only runs during market hours (9:30 AM - 4:00 PM ET)
- Check internet connection
- Verify Alpaca account has data permissions

**"No trades executed"**
- Market conditions may not meet criteria (IV rank, price moves)
- Lower min_iv_rank or min_price_move for testing
- Check logs for Claude analysis results

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or issues:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review Alpaca API documentation: [alpaca.markets/docs](https://alpaca.markets/docs)
- Review Anthropic API documentation: [docs.anthropic.com](https://docs.anthropic.com)

---

**Disclaimer**: This software is for educational purposes only. Trading involves significant financial risk. Always consult with a financial advisor before making investment decisions.