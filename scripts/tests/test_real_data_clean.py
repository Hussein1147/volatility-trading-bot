#!/usr/bin/env python3
"""
Test that we're getting real data from all our API sources
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.backtest.data_fetcher import AlpacaDataFetcher
from src.backtest.tastytrade_api import TastyTradeDataFetcher
from src.backtest.polygon_options_fetcher import PolygonOptionsFetcher

async def test_data_sources():
    """Test all real data sources"""
    print(f"\n{'='*60}")
    print(f"Testing Real Data Sources for Options Trading")
    print(f"{'='*60}\n")
    
    # Initialize fetchers
    alpaca_fetcher = AlpacaDataFetcher()
    tastytrade_fetcher = TastyTradeDataFetcher()
    polygon_fetcher = PolygonOptionsFetcher()
    
    # Test dates
    recent_date = datetime(2024, 11, 15)  # Recent date for Alpaca
    historical_date = datetime(2023, 10, 15)  # Historical date for Polygon
    
    symbol = 'SPY'
    
    # 1. Test TastyTrade IV Rank
    print(f"1. Testing TastyTrade IV Rank Data...")
    try:
        iv_rank = await tastytrade_fetcher.get_iv_rank(symbol, recent_date)
        if iv_rank is not None:
            print(f"✓ TastyTrade IV Rank for {symbol}: {iv_rank:.1f}")
            
            # Get full metrics
            metrics = await tastytrade_fetcher.get_full_metrics(symbol)
            if metrics:
                print(f"  - IV Percentile: {metrics.get('iv_percentile', 'N/A')}")
                print(f"  - Historical Vol 30: {metrics.get('historical_volatility_30', 'N/A')}")
        else:
            print(f"✗ No TastyTrade data available (check credentials)")
    except Exception as e:
        print(f"✗ TastyTrade error: {e}")
    
    # 2. Test Polygon Historical Options
    print(f"\n2. Testing Polygon Historical Options Data...")
    if polygon_fetcher.api_key:
        try:
            # Get historical options chain
            chain = await polygon_fetcher.get_options_chain(symbol, historical_date, 30, 45)
            if chain:
                first_expiry = list(chain.keys())[0]
                expiry_data = chain[first_expiry]
                print(f"✓ Polygon found {len(chain)} expirations")
                print(f"  - First expiry: {first_expiry} ({expiry_data['dte']} DTE)")
                print(f"  - Calls: {len(expiry_data['calls'])} strikes")
                print(f"  - Puts: {len(expiry_data['puts'])} strikes")
                
                # Check for Greeks in snapshot
                snapshot = await polygon_fetcher.get_option_snapshot(symbol)
                if snapshot:
                    # Find first option with Greeks
                    for ticker, data in snapshot.items():
                        if data.get('delta') is not None:
                            print(f"✓ Polygon Greeks available:")
                            print(f"  - Sample: {ticker}")
                            print(f"  - Delta: {data['delta']:.3f}")
                            print(f"  - Gamma: {data.get('gamma', 'N/A')}")
                            print(f"  - Theta: {data.get('theta', 'N/A')}")
                            print(f"  - Vega: {data.get('vega', 'N/A')}")
                            break
                else:
                    print(f"  - Greeks require paid Polygon subscription")
            else:
                print(f"✗ No Polygon historical data found")
        except Exception as e:
            print(f"✗ Polygon error: {e}")
    else:
        print(f"✗ No Polygon API key configured")
    
    # 3. Test Alpaca Options Data
    print(f"\n3. Testing Alpaca Options Data (Feb 2024+)...")
    try:
        # Get options chain for recent date
        options_chain = await alpaca_fetcher.get_options_chain(symbol, recent_date, 30, 45)
        
        if options_chain:
            print(f"✓ Alpaca returned {len(options_chain)} options")
            
            # Check for Greeks
            options_with_greeks = [opt for opt in options_chain if opt.get('delta') is not None]
            if options_with_greeks:
                sample = options_with_greeks[0]
                print(f"✓ Alpaca Greeks available:")
                print(f"  - Sample: {sample['symbol']}")
                print(f"  - Delta: {sample['delta']:.3f}")
                print(f"  - Gamma: {sample.get('gamma', 'N/A')}")
                print(f"  - Theta: {sample.get('theta', 'N/A')}")
                print(f"  - Vega: {sample.get('vega', 'N/A')}")
            else:
                print(f"  - No Greeks found in Alpaca data")
            
            # Show data source used
            if any('polygon' in str(opt.get('source', '')).lower() for opt in options_chain):
                print(f"  - Data source: Polygon (via integration)")
            elif all(opt.get('delta') is None for opt in options_chain):
                print(f"  - Data source: Simulated (no real Greeks)")
            else:
                print(f"  - Data source: Alpaca (real data)")
        else:
            print(f"✗ No options data returned")
            
    except Exception as e:
        print(f"✗ Alpaca error: {e}")
    
    # 4. Test Integrated Data Fetcher
    print(f"\n4. Testing Integrated Data Fetcher...")
    
    # Test historical date (should use Polygon or simulation)
    print(f"\nHistorical date ({historical_date.strftime('%Y-%m-%d')}):")
    hist_chain = await alpaca_fetcher.get_options_chain(symbol, historical_date, 30, 45)
    if hist_chain:
        print(f"✓ Got {len(hist_chain)} options")
        sample = hist_chain[0] if hist_chain else None
        if sample:
            data_type = "Real" if sample.get('delta') is not None else "Simulated"
            print(f"  - Data type: {data_type}")
    
    # Test recent date (should use Alpaca)
    print(f"\nRecent date ({recent_date.strftime('%Y-%m-%d')}):")
    recent_chain = await alpaca_fetcher.get_options_chain(symbol, recent_date, 30, 45)
    if recent_chain:
        print(f"✓ Got {len(recent_chain)} options")
        sample = recent_chain[0] if recent_chain else None
        if sample:
            data_type = "Real" if sample.get('delta') is not None else "Simulated"
            print(f"  - Data type: {data_type}")
    
    # Test IV Rank integration
    print(f"\nTesting IV Rank integration:")
    vol_data = await alpaca_fetcher.get_historical_volatility_data(symbol, recent_date, 365)
    if vol_data:
        print(f"✓ IV Rank: {vol_data['iv_rank']:.1f}")
        print(f"  - Source: {'TastyTrade' if vol_data.get('iv_rank_source') == 'tastytrade' else 'Calculated'}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"{'='*60}")
    
    data_sources = []
    if tastytrade_fetcher.api._cache:
        data_sources.append("TastyTrade (IV Rank)")
    if polygon_fetcher.api_key:
        data_sources.append("Polygon (Historical Options)")
    if alpaca_fetcher.has_options_access:
        data_sources.append("Alpaca (Recent Options)")
    
    if data_sources:
        print(f"✓ Active real data sources:")
        for source in data_sources:
            print(f"  - {source}")
    else:
        print(f"✗ No real data sources active - using simulation only")
    
    print(f"\nRecommendations:")
    if not polygon_fetcher.api_key:
        print(f"  - Add POLYGON_API_KEY for historical options data")
    if not tastytrade_fetcher.api.username:
        print(f"  - Add TASTYTRADE_USERNAME/PASSWORD for real IV rank")
    if not alpaca_fetcher.has_options_access:
        print(f"  - Check Alpaca options subscription for recent data")

if __name__ == "__main__":
    asyncio.run(test_data_sources())