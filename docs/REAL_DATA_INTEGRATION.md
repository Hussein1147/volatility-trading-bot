# Real Data Integration

This document explains how the volatility trading bot uses REAL options data from multiple API sources, prioritizing actual market data over simulations.

## Data Source Priority

The system uses a hierarchical approach to ensure we always get the most accurate real data available:

### 1. **Polygon.io** (Primary for Historical Data)
- **What it provides**: Historical options prices, volumes, and sometimes Greeks
- **Coverage**: Extensive historical data going back years
- **When used**: First choice for any historical backtesting
- **Greeks**: Available with paid subscription via snapshot API

### 2. **Alpaca Markets** (Primary for Recent Data)
- **What it provides**: Options chains with Greeks (delta, gamma, theta, vega, rho)
- **Coverage**: February 2024 onwards
- **When used**: For recent dates when Polygon data isn't available
- **Greeks**: Included in the options chain data

### 3. **TastyTrade** (IV Rank Specialist)
- **What it provides**: Real-time IV rank and IV percentile
- **Coverage**: Current market data
- **When used**: For accurate IV rank calculations instead of estimations
- **Special feature**: Professional-grade volatility metrics

### 4. **Simulation** (Last Resort Only)
- **When used**: ONLY when no real data is available from any source
- **Purpose**: Allows backtesting for dates without API coverage
- **Note**: Clearly logged when simulation is used

## Configuration

### Required Environment Variables

```bash
# Alpaca (Required)
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret

# Polygon (Recommended for historical data)
POLYGON_API_KEY=your_polygon_key

# TastyTrade (Recommended for IV rank)
TASTYTRADE_USERNAME=your_username
TASTYTRADE_PASSWORD=your_password
TASTYTRADE_ACCOUNT=your_account_number
```

## How It Works

### Options Chain Fetching
```python
# The data fetcher tries sources in order:
1. Polygon historical data (if date < today)
2. Alpaca data (if date >= Feb 2024)
3. Simulation (only if both fail)
```

### Greeks Data
```python
# Greeks are obtained from:
1. Alpaca's nested Greeks structure (when available)
2. Polygon's snapshot API (requires subscription)
3. Black-Scholes calculation (only when needed for strike selection)
```

### IV Rank
```python
# IV rank comes from:
1. TastyTrade API (real professional data)
2. Historical volatility calculation (if TastyTrade unavailable)
```

## Verification

Run the test script to verify your data sources:

```bash
python scripts/tests/test_real_data_sources.py
```

This will show:
- ✓ Which APIs are properly configured
- ✓ What data each source is providing
- ✓ Whether you're getting real Greeks or simulated data

## Example Output

When using real data, you'll see logs like:
```
Using real Polygon options data for SPY on 2023-10-15
Using real TastyTrade IV rank for SPY: 75.3
Found Alpaca Greeks for SPY241220C00450000: delta=0.453
```

When falling back to simulation:
```
Date 2020-01-15 is before Alpaca options data availability and no Polygon data found
```

## Backtesting with Real Data

The backtest engine automatically uses the best available data:

1. **For dates before Feb 2024**: Uses Polygon if available
2. **For recent dates**: Uses Alpaca with real Greeks
3. **For IV metrics**: Always tries TastyTrade first

## Important Notes

1. **No Simulated Greeks**: When we have real options data but no Greeks, we attempt to fetch them from alternative sources before calculating
2. **Transparent Logging**: Every data source switch is logged so you know exactly what data you're using
3. **Professional Strategy**: Uses 0.15 delta targeting which requires accurate Greeks data
4. **Multi-Book Support**: Different expiration cycles may use different data sources

## API Costs

- **Alpaca**: Included with brokerage account
- **Polygon**: Free tier available, paid for more requests
- **TastyTrade**: Free with account

## Troubleshooting

If you're seeing simulated data when you expect real data:

1. Check your API credentials are set correctly
2. Verify the date range (Alpaca only has data from Feb 2024)
3. Check API subscription levels (Polygon Greeks need paid plan)
4. Run the test script to diagnose issues

Remember: The goal is to use REAL market data whenever possible. Simulation is only a fallback to allow historical backtesting when API data isn't available.