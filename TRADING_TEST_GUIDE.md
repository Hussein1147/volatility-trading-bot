# Trading Lifecycle Test Suite Guide

## Overview
This comprehensive test suite simulates the full lifecycle of options trades using Alpaca's data structure. It validates:
- Market data simulation
- Order entry and execution
- Trade lifecycle management
- Analytics and performance tracking
- Edge cases and error handling

## Key Components

### 1. AlpacaDataSimulator
Simulates realistic market data following Alpaca's format:
- **Stock Quotes**: Real-time bid/ask/last prices with volume
- **Option Chains**: Full option chains with accurate Greeks using Black-Scholes
- **Price Movement**: Simulates underlying and volatility changes
- **Symbol Format**: Uses Alpaca's format (e.g., `AAPL240119C00100000`)

### 2. OrderSimulator
Simulates order management:
- **Order Submission**: Market and limit orders
- **Execution**: Realistic fill prices based on bid/ask
- **Position Tracking**: Maintains accurate position state
- **Order States**: Follows Alpaca's order lifecycle

### 3. TradingLifecycleTest
Complete test scenarios:
- **Market Data Tests**: Validates data generation and Greeks
- **Order Flow Tests**: Tests order entry through execution
- **Trade Lifecycle**: Full trade from entry to exit
- **Analytics Tests**: Performance metrics and tracking
- **Edge Cases**: Extreme conditions and error handling

## Running the Tests

### Basic Usage
```bash
# Activate virtual environment
source trading_bot_env/bin/activate

# Run full test suite
python test_trading_lifecycle.py
```

### Expected Output
```
============================================================
TRADING LIFECYCLE TEST SUITE
============================================================
Started at: 2025-05-31 18:30:00

🔍 Testing Market Data Simulation...
✅ PASS: Stock quote simulation - SPY: $450.23
✅ PASS: Option chain simulation - Generated 42 contracts
✅ PASS: Greeks calculation - Delta: 0.5234, IV: 0.1823

🔍 Testing Order Entry & Execution...
✅ PASS: Sell order execution - Sold SPY240215C00450000 @ $5.25
✅ PASS: Buy order execution - Bought SPY240215C00455000 @ $3.10
✅ PASS: Position tracking - Tracking 2 positions

🔍 Testing Complete Trade Lifecycle...
✅ PASS: Trade creation - Created put_credit for $215.00 credit
✅ PASS: P&L calculation - Unrealized P&L: $-43.50 after 2% drop
✅ PASS: Profit target detection - Closing: profit target reached (35%)
✅ PASS: Stop loss detection - Closing: stop loss triggered (75%)
✅ PASS: Time stop detection - Closing: time stop at 3 DTE

🔍 Testing Analytics & Performance Tracking...
✅ PASS: Trade summary calculation - Win rate: 60.0%
✅ PASS: Daily P&L tracking - Today's P&L: $127.50
✅ PASS: Greeks aggregation - Portfolio Delta: -0.1234

🔍 Testing Edge Cases...
✅ PASS: Expired contract rejection
✅ PASS: Invalid symbol handling
✅ PASS: Extreme market movement - Price dropped from $10.0 to $3.45

============================================================
TEST SUMMARY
============================================================
Passed: 5/5
Success Rate: 100.0%
✅ ALL TESTS PASSED - Trading lifecycle fully validated!

📄 Detailed report saved to: trading_lifecycle_test_report.json
```

## Test Scenarios

### 1. Market Data Simulation
- **Stock Quotes**: ±2% random movement from base prices
- **Option Chains**: 21 strikes around ATM, accurate Greeks
- **IV Smile**: Implied volatility increases with moneyness
- **Bid-Ask Spreads**: Realistic 2% spreads

### 2. Order Execution
- **Market Orders**: Immediate execution at bid/ask
- **Fill Prices**: Buy at ask, sell at bid
- **Position Updates**: Accurate quantity and average price tracking

### 3. Trade Lifecycle
- **Credit Spread Entry**: Sell ATM, buy OTM
- **P&L Calculation**: Real-time based on option prices
- **Exit Conditions**:
  - Profit target: 35% of max profit
  - Stop loss: 75% of max loss
  - Time stop: 5 DTE

### 4. Analytics Tracking
- **Win Rate**: Percentage of profitable trades
- **Average Win/Loss**: Mean P&L for winners and losers
- **Daily P&L**: Today's realized gains/losses
- **Portfolio Greeks**: Aggregated Delta, Gamma, Theta, Vega

### 5. Edge Cases
- **Expired Contracts**: Proper rejection
- **Invalid Symbols**: Graceful fallback
- **Market Crashes**: 10% drops with IV spikes
- **Data Gaps**: Handle missing data

## Customization

### Modify Base Prices
```python
self.base_prices = {
    'SPY': 450.00,
    'QQQ': 380.00,
    'IWM': 190.00,
    'AAPL': 180.00
}
```

### Adjust Volatility
```python
self.volatility_map = {
    'SPY': 0.18,   # 18% annualized
    'QQQ': 0.22,   # 22% annualized
    'IWM': 0.25,   # 25% annualized
    'AAPL': 0.28   # 28% annualized
}
```

### Configure Trade Rules
```python
@dataclass
class TradeManagementRules:
    profit_target_percent: float = 0.35  # 35% of max profit
    stop_loss_percent: float = 0.75      # 75% of max loss
    time_stop_dte: int = 5               # Close at 5 DTE
```

## Integration with Live Trading

The test suite uses the same data structures as the live trading system:

1. **OptionContract**: Compatible with both test and live data
2. **Trade**: Same object used in production
3. **Order Format**: Matches Alpaca's API exactly

This ensures tests accurately reflect production behavior.

## Troubleshooting

### Missing Dependencies
```bash
pip install scipy pandas numpy
```

### Import Errors
Ensure you're in the project directory:
```bash
cd /Users/djibrilkeita/Desktop/volatility-trading-bot
```

### Test Failures
Check the detailed report:
```bash
cat trading_lifecycle_test_report.json | jq '.'
```

## Next Steps

1. **Add More Symbols**: Extend base_prices and volatility_map
2. **Test More Strategies**: Iron condors, butterflies, etc.
3. **Stress Testing**: Simulate flash crashes, circuit breakers
4. **Performance Testing**: Measure execution speed
5. **Integration Tests**: Connect to paper trading account

## Important Notes

- All prices and Greeks are simulated but follow real market dynamics
- The Black-Scholes model is used for accurate option pricing
- Position tracking mirrors Alpaca's actual behavior
- Test data can be saved and replayed for regression testing