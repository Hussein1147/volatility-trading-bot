"""
Test free options data APIs to see what's available without paid subscriptions
"""

import asyncio
import aiohttp
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class FreeOptionsDataExplorer:
    """Explore free options data sources"""
    
    async def test_yahoo_finance(self):
        """Test Yahoo Finance options data"""
        print("\n=== Yahoo Finance Options Data ===")
        
        try:
            # Test symbols
            symbols = ['SPY', 'QQQ', 'IWM']
            
            for symbol in symbols:
                print(f"\n{symbol}:")
                ticker = yf.Ticker(symbol)
                
                # Get basic info
                info = ticker.info
                print(f"  Current Price: ${info.get('currentPrice', 'N/A')}")
                print(f"  52-week IV Range: Not available in Yahoo Finance")
                
                # Get options expirations
                expirations = ticker.options
                print(f"  Available expirations: {len(expirations)}")
                
                if expirations:
                    # Get first expiration
                    first_exp = expirations[0]
                    print(f"  Nearest expiration: {first_exp}")
                    
                    # Get option chain
                    opt_chain = ticker.option_chain(first_exp)
                    
                    # Analyze calls
                    calls = opt_chain.calls
                    print(f"\n  Calls data:")
                    print(f"    Total strikes: {len(calls)}")
                    print(f"    Available columns: {list(calls.columns)}")
                    
                    # Check for IV data
                    if 'impliedVolatility' in calls.columns:
                        print(f"    ✓ Implied Volatility available")
                        # Get ATM option
                        current_price = info.get('currentPrice', 0)
                        if current_price:
                            atm_strike = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]
                            if not atm_strike.empty:
                                iv = atm_strike['impliedVolatility'].iloc[0]
                                print(f"    ATM IV: {iv:.2%}")
                    else:
                        print(f"    ✗ No IV data")
                        
                    # Sample data
                    print(f"\n  Sample option data (first 3 strikes):")
                    print(calls[['strike', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].head(3))
                    
        except Exception as e:
            print(f"Error: {e}")
            
    async def test_cboe_data(self):
        """Test CBOE free data endpoints"""
        print("\n\n=== CBOE Free Data ===")
        
        # CBOE provides some free delayed quotes
        base_url = "https://www.cboe.com/delayed_quotes"
        
        async with aiohttp.ClientSession() as session:
            # Test VIX data (free)
            vix_url = "https://cdn.cboe.com/api/global/delayed_quotes/charts/_VIX.json"
            
            try:
                async with session.get(vix_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"VIX Data Available: Yes")
                        print(f"  Current VIX: {data.get('data', {}).get('last', 'N/A')}")
                    else:
                        print(f"VIX Data: Not accessible (Status: {response.status})")
            except Exception as e:
                print(f"VIX Error: {e}")
                
    async def test_alpha_vantage(self):
        """Test Alpha Vantage free tier"""
        print("\n\n=== Alpha Vantage (Free Tier) ===")
        print("Alpha Vantage offers:")
        print("  - 5 API calls per minute")
        print("  - Historical options data: No")
        print("  - Real-time options: No")
        print("  - IV Rank: No")
        print("  - Useful for: Stock price data only")
        
    def analyze_free_alternatives(self):
        """Analyze what we can calculate ourselves"""
        print("\n\n=== DIY IV Rank Calculation ===")
        print("What we can calculate from free data:")
        print("  1. Historical Volatility (HV) from price data")
        print("  2. Realized Volatility from returns")
        print("  3. IV approximation from ATM options (Yahoo)")
        print("  4. Simple IV rank based on HV percentiles")
        
        # Example calculation
        print("\nExample: Calculate HV-based 'IV Rank' for SPY")
        
        try:
            spy = yf.Ticker('SPY')
            
            # Get 1 year of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            hist = spy.history(start=start_date, end=end_date)
            
            # Calculate 30-day rolling HV
            returns = hist['Close'].pct_change()
            rolling_vol = returns.rolling(window=30).std() * np.sqrt(252) * 100
            
            # Calculate HV rank (percentile over past year)
            current_hv = rolling_vol.iloc[-1]
            hv_rank = (rolling_vol < current_hv).sum() / len(rolling_vol) * 100
            
            print(f"  Current 30-day HV: {current_hv:.1f}%")
            print(f"  HV Rank (percentile): {hv_rank:.1f}")
            print(f"  52-week HV High: {rolling_vol.max():.1f}%")
            print(f"  52-week HV Low: {rolling_vol.min():.1f}%")
            
            # Get current IV from options
            expirations = spy.options
            if expirations:
                # Get ~30 DTE options
                target_date = datetime.now() + timedelta(days=30)
                
                # Find closest expiration
                exp_dates = [datetime.strptime(exp, '%Y-%m-%d') for exp in expirations]
                closest_exp = min(exp_dates, key=lambda x: abs((x - target_date).days))
                closest_exp_str = closest_exp.strftime('%Y-%m-%d')
                
                # Get ATM IV
                opt_chain = spy.option_chain(closest_exp_str)
                current_price = hist['Close'].iloc[-1]
                
                # Find ATM call
                calls = opt_chain.calls
                atm_idx = (calls['strike'] - current_price).abs().argsort()[0]
                atm_iv = calls.iloc[atm_idx]['impliedVolatility'] * 100
                
                print(f"\n  Current ATM IV (~30 DTE): {atm_iv:.1f}%")
                print(f"  IV Premium over HV: {atm_iv - current_hv:.1f}%")
                
        except Exception as e:
            print(f"  Calculation error: {e}")


async def main():
    """Run all tests"""
    explorer = FreeOptionsDataExplorer()
    
    # Test each source
    await explorer.test_yahoo_finance()
    await explorer.test_cboe_data()
    await explorer.test_alpha_vantage()
    
    # Show DIY calculations
    explorer.analyze_free_alternatives()
    
    print("\n\n=== SUMMARY: Available Free Options Data ===")
    print("\n✓ Yahoo Finance (yfinance):")
    print("  - Real-time option chains")
    print("  - Implied volatility for each strike")
    print("  - Bid/ask spreads")
    print("  - Volume and open interest")
    print("  - Greeks (sometimes)")
    print("  ✗ No IV rank or IV percentile")
    print("  ✗ No historical IV data")
    
    print("\n✓ What we can build ourselves:")
    print("  - HV-based volatility rank")
    print("  - IV term structure analysis")
    print("  - Volatility surface from option chains")
    print("  - Custom IV rank using ATM IV history")
    
    print("\n💡 Recommendation:")
    print("  For accurate backtesting, we can:")
    print("  1. Use Yahoo Finance for option chains")
    print("  2. Calculate our own HV-based 'volatility rank'")
    print("  3. Store historical IV data as we collect it")
    print("  4. Use TastyTrade when available for true IV rank")


if __name__ == "__main__":
    asyncio.run(main())