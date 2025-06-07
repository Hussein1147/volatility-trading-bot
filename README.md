# Volatility Trading Bot

An advanced AI-powered options trading system that uses Claude AI to identify and execute credit spread strategies during market volatility spikes. Features professional-grade backtesting with real options data and sophisticated risk management.

## 🚀 Key Features

### Trading Capabilities
- **Real-time Market Monitoring**: Continuously scans major ETFs (SPY, QQQ, IWM, DIA, XLE, XLK) for volatility events
- **AI-Powered Analysis**: Uses Claude Sonnet 4 for intelligent trade decisions with confidence scoring
- **Automated Execution**: Executes credit spreads through Alpaca Trading API
- **Dynamic Position Sizing**: IV-aware sizing that scales with market volatility (up to 2x at high IV)
- **Professional Risk Management**: Tiered profit targets, enhanced stop losses, and time-based exits

### Advanced Features
- **Return-Boost Package v1**: Short-dated options strategy (7-14 DTE) with enhanced exit rules
- **Confidence Score Breakdown**: Full transparency into AI decision-making factors
- **Real Options Data Integration**: TastyTrade, Polygon, and Alpaca data sources
- **Synthetic Pricing Engine**: Black-Scholes model for backtesting any date range
- **Delta-Based Strike Selection**: Professional 16-delta targeting for optimal risk/reward

### Dashboard Systems
- **Main Trading Dashboard**: Live monitoring, position tracking, and bot control
- **Advanced Backtesting Dashboard**: Comprehensive historical analysis with real-time progress
- **Activity Logging**: Real-time trade decisions and AI reasoning display

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

#### Launch Both Dashboards (Recommended)
```bash
# Start both dashboards in background
nohup python3 -m streamlit run src/ui/dashboard.py --server.port 8501 &
nohup python3 -m streamlit run src/ui/backtest_dashboard.py --server.port 8502 &

# Access at:
# Main Dashboard: http://localhost:8501
# Backtest Dashboard: http://localhost:8502
```

#### Individual Launch Commands
```bash
# Main Trading Dashboard
python3 scripts/production/run_dashboard.py

# Backtesting Dashboard  
python3 scripts/production/run_backtest.py
```

## Project Structure

```
volatility-trading-bot/
├── src/
│   ├── core/              # Core trading logic
│   │   ├── trade_manager.py         # Trade execution and management
│   │   ├── volatility_bot.py        # Main bot logic
│   │   ├── position_tracker.py      # Position monitoring
│   │   ├── position_sizer.py        # Dynamic position sizing
│   │   ├── strike_selector.py       # Delta-based strike selection
│   │   └── greeks_calculator.py     # Options Greeks calculations
│   ├── data/              # Data management
│   │   ├── trade_db.py             # SQLite database interface
│   │   ├── backtest_db.py          # Backtest results storage
│   │   └── simulated_pnl.py        # P&L tracking for dev mode
│   ├── ui/                # User interfaces
│   │   ├── dashboard.py            # Main trading dashboard
│   │   └── backtest_dashboard.py   # Advanced backtesting interface
│   ├── backtest/          # Backtesting framework
│   │   ├── backtest_engine.py      # Core backtesting with AI
│   │   ├── data_fetcher.py         # Multi-source data integration
│   │   ├── visualizer.py           # Results visualization
│   │   ├── advanced_visualizer.py  # Greeks & confidence analysis
│   │   └── ai_provider.py          # Claude/Gemini AI interface
│   ├── engines/           # Trading engines
│   │   └── synthetic_pricer.py     # Black-Scholes pricing engine
│   └── strategies/        # Trading strategies
│       └── credit_spread.py        # Short-dated options strategy
├── scripts/               # Utility scripts
│   ├── production/               # Production-ready scripts
│   └── tests/                    # Test scripts
├── tests/                 # Comprehensive test suite
├── docs/                  # Documentation
└── requirements.txt       # Python dependencies
```

## Trading Strategy

### Current Strategy: Return-Boost Package v1

The bot implements an advanced volatility-based credit spread strategy with short-dated options:

1. **Signal Detection**: 
   - Price moves > 1.5% with IV rank > 40
   - AI analyzes market context and technical indicators

2. **Direction Analysis**: 
   - Big move DOWN + Technical confirmation → Sell CALL credit spreads
   - Big move UP + Technical confirmation → Sell PUT credit spreads
   - Claude AI provides confidence scoring (0-100%)

3. **Strike Selection**: 
   - Delta-based: Target 16-delta (84% probability of profit)
   - Fallback: 3% out-of-the-money

4. **Expiration Strategy**:
   - PRIMARY BOOK: 7-14 DTE for maximum gamma/theta
   - INCOME-POP: High IV opportunities with quick exits
   - Dynamic selection based on market conditions

5. **Position Sizing (IV-Aware)**:
   - Base: 3% risk per trade at 70% confidence
   - IV Boost: Up to 2x sizing at high IV (capped at 8%)
   - Scales with confidence: 70% → 3%, 80% → 5%, 90% → 8%

6. **Enhanced Exit Rules (Tiered)**:
   - **Tier 1**: Exit 40% at +50% of credit
   - **Tier 2**: Exit 40% at +75% of credit  
   - **Final 20%**: Ride for +150% potential
   - **Stop Loss**: -250% of credit (allows recovery)
   - **Time Stop**: 7 DTE for risk management

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

## Backtesting Framework

The advanced backtesting system provides professional-grade analysis:

### Data Sources
- **Stock Data**: Real historical prices from Alpaca
- **Options Data**: 
  - TastyTrade: IV Rank and volatility metrics
  - Polygon: Historical options chains
  - Alpaca: Recent options with Greeks (Feb 2024+)
- **Synthetic Pricing**: Black-Scholes model for any date range

### Features
- **Real-Time Progress**: Live updates during backtest execution
- **AI Integration**: Same Claude analysis as live trading
- **Confidence Breakdown**: Detailed scoring transparency
- **Advanced Visualizations**:
  - Equity curves with drawdown analysis
  - Greeks evolution over time
  - Confidence score vs P&L correlation
  - Performance heatmaps by month/day
  - Risk metrics dashboard

### Running a Backtest

1. Launch the backtesting dashboard
2. Configure parameters:
   - Date range and symbols
   - Strategy settings (IV rank, price move thresholds)
   - Exit rules (profit targets, stop losses)
   - Pricing method (real data or synthetic)
3. Click "Run Backtest"
4. Monitor real-time progress and activity log
5. Analyze comprehensive results

### Saved Results
All backtests are automatically saved with:
- Complete trade history
- AI decision logs
- Performance metrics
- Ability to compare multiple runs

## System Verification

Run the verification script to ensure everything is configured correctly:

```bash
python3 scripts/production/verify_system.py
```

This checks:
- ✅ Python version and environment
- ✅ API connectivity (Claude, Alpaca)
- ✅ Database setup and migrations
- ✅ All dependencies installed
- ✅ Dashboard accessibility
- ✅ Backtest engine functionality

## API Documentation

### Data Sources

- **Stock Data**: Alpaca Markets (real-time and historical)
- **Options Data**: 
  - Alpaca Markets (Feb 2024+, with Greeks)
  - TastyTrade (IV rank and volatility metrics)
  - Polygon (historical options chains)
- **AI Analysis**: Anthropic Claude Sonnet 4 (primary)
- **Fallback AI**: Google Gemini 1.5 Flash

### Database Schema

The bot uses SQLite for local storage:

**Main Tables**:
- `trades`: Complete trade history with P&L
- `market_scans`: All market volatility events
- `bot_logs`: System events and errors
- `claude_analyses`: AI decision history

**Backtest Tables**:
- `backtest_runs`: Run configurations and results
- `backtest_trades`: Individual trade records
- `backtest_analyses`: AI decisions during backtests

## Recent Updates

### v2.0 - Return-Boost Package
- ✨ Short-dated options strategy (7-14 DTE)
- 📊 Confidence score breakdown visualization
- 🔬 Synthetic pricing with Black-Scholes
- 📈 Real options data from multiple sources
- 🎯 Delta-based strike selection
- 💰 IV-aware dynamic position sizing

### v1.5 - Advanced Backtesting
- 🚀 Real-time progress tracking
- 📋 Live activity logging
- 💾 Automatic result saving
- 📊 Greeks analysis charts
- 🔥 Performance heatmaps

## Documentation

- **[Professional Strategy Guide](docs/PROFESSIONAL_STRATEGY.md)**: Detailed strategy rules
- **[Migration Plan](docs/MIGRATION_PLAN.md)**: Upgrading to professional strategy
- **[AI Integration](docs/AI_POWERED_TRADING_SUMMARY.md)**: Claude AI implementation
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Cloud deployment instructions

## Testing

Run the comprehensive test suite:

```bash
# Test backtesting with progress
python3 -m tests.integration.backtest.test_backtest_with_progress

# Test real data integration
python3 -m tests.integration.data.test_real_data_backtest

# Test AI integration
python3 scripts/tests/test_claude_integration.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure quality
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Disclaimer

**IMPORTANT**: This bot is for educational purposes. Trading options involves substantial risk of loss. Past performance does not guarantee future results. Always test thoroughly with paper trading before using real money. The developers are not responsible for any financial losses incurred through the use of this software.

## Support

- 📖 Check the [documentation](docs/) for detailed guides
- 🐛 Report issues on [GitHub Issues](https://github.com/Hussein1147/volatility-trading-bot/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/Hussein1147/volatility-trading-bot/discussions)