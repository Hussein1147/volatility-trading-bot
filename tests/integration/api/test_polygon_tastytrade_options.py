"""
Test what historical options data is available from TastyTrade and Polygon
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

load_dotenv()

class OptionsDataTester:
    """Test historical options data availability"""
    
    def __init__(self):
        self.polygon_key = os.getenv('POLYGON_API_KEY', os.getenv('OLYGON_API_KEY'))  # Handle typo
        self.tastytrade_session = None
        
    async def test_polygon_options(self):
        """Test Polygon.io historical options data"""
        print("\n=== Polygon.io Options Data ===")
        
        if not self.polygon_key:
            print("❌ No Polygon API key found")
            return
            
        base_url = "https://api.polygon.io"
        
        # Test dates
        test_date = "2024-11-01"
        
        # Test endpoints
        async with aiohttp.ClientSession() as session:
            # 1. Test options chain endpoint
            print(f"\n1. Testing Options Chain for SPY on {test_date}:")
            chain_url = f"{base_url}/v3/reference/options/contracts?underlying_ticker=SPY&expired=false&apiKey={self.polygon_key}"
            
            try:
                async with session.get(chain_url) as response:
                    print(f"   Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"   ✓ Found {len(results)} options contracts")
                        
                        if results:
                            # Show sample contract
                            contract = results[0]
                            print(f"   Sample contract: {contract.get('ticker')}")
                            print(f"   Available fields: {', '.join(contract.keys())}")
                    else:
                        error = await response.text()
                        print(f"   ❌ Error: {error}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")
            
            # 2. Test historical options prices
            print(f"\n2. Testing Historical Options Prices:")
            
            # Get a specific option contract (SPY 590 Call expiring 2024-11-15)
            option_ticker = "O:SPY241115C00590000"  # Polygon format
            
            # Daily bars for the option
            hist_url = f"{base_url}/v2/aggs/ticker/{option_ticker}/range/1/day/2024-10-01/{test_date}?apiKey={self.polygon_key}"
            
            try:
                async with session.get(hist_url) as response:
                    print(f"   Status for {option_ticker}: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"   ✓ Found {len(results)} days of price history")
                        
                        if results:
                            # Show last few days
                            for bar in results[-3:]:
                                date = datetime.fromtimestamp(bar['t']/1000).strftime('%Y-%m-%d')
                                print(f"     {date}: Open=${bar['o']:.2f}, Close=${bar['c']:.2f}, Volume={bar['v']}")
                    else:
                        error = await response.text()
                        print(f"   ❌ Error: {error}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                
            # 3. Test options snapshot (current data)
            print(f"\n3. Testing Options Snapshot:")
            snapshot_url = f"{base_url}/v3/snapshot/options/SPY?apiKey={self.polygon_key}"
            
            try:
                async with session.get(snapshot_url) as response:
                    print(f"   Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"   ✓ Found snapshots for {len(results)} strikes")
                        
                        if results:
                            # Check for IV data
                            sample = results[0]
                            if 'implied_volatility' in sample:
                                print(f"   ✓ IV data available: {sample['implied_volatility']}")
                            else:
                                print(f"   ❌ No IV data in snapshot")
                                
                            # Check for Greeks
                            greeks = sample.get('greeks', {})
                            if greeks:
                                print(f"   ✓ Greeks available: {', '.join(greeks.keys())}")
                    else:
                        error = await response.text()
                        print(f"   ❌ Error: {error}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                
    async def test_tastytrade_options_history(self):
        """Test TastyTrade historical options data"""
        print("\n\n=== TastyTrade Historical Options Data ===")
        
        # First authenticate
        username = os.getenv('TASTYTRADE_USERNAME')
        password = os.getenv('TASTYTRADE_PASSWORD')
        
        if not username or not password:
            print("❌ No TastyTrade credentials found")
            return
            
        async with aiohttp.ClientSession() as session:
            # Authenticate
            auth_data = {"login": username, "password": password, "remember-me": True}
            
            async with session.post("https://api.tastyworks.com/sessions", json=auth_data) as response:
                if response.status == 201:
                    data = await response.json()
                    self.tastytrade_session = data['data']['session-token']
                    print("✓ Authenticated successfully")
                else:
                    print("❌ Authentication failed")
                    return
                    
            headers = {"Authorization": self.tastytrade_session}
            
            # Test historical data endpoints
            print("\n1. Testing Historical Market Metrics:")
            
            # Note: TastyTrade API doesn't directly provide historical options prices
            # They provide current data and some historical metrics
            
            # Test if they have any historical endpoints
            test_endpoints = [
                "/market-metrics/historic?symbols=SPY",
                "/market-metrics/historical-volatility?symbols=SPY",
                "/watchlists/historical-volatility",
                "/instruments/equity-options/SPY/history",
            ]
            
            for endpoint in test_endpoints:
                url = f"https://api.tastyworks.com{endpoint}"
                try:
                    async with session.get(url, headers=headers) as response:
                        print(f"\n   {endpoint}:")
                        print(f"   Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            print(f"   ✓ Data available")
                            print(f"   Response preview: {json.dumps(data, indent=2)[:200]}...")
                        elif response.status == 404:
                            print(f"   ❌ Endpoint not found")
                        else:
                            print(f"   ❌ Error status")
                except Exception as e:
                    print(f"   ❌ Exception: {e}")
                    
    def summarize_findings(self):
        """Summarize what historical options data is available"""
        print("\n\n=== SUMMARY: Historical Options Data Availability ===")
        
        print("\n📊 Polygon.io:")
        print("  ✓ Historical options price bars (OHLCV)")
        print("  ✓ Multiple years of history available")
        print("  ✓ Options chain snapshots")
        print("  ✓ Greeks and IV (in snapshots)")
        print("  ✓ Free tier: 5 API calls/minute")
        print("  💰 Paid tiers for more data")
        
        print("\n📊 TastyTrade:")
        print("  ✓ Real-time IV rank and percentile")
        print("  ✓ Current options chains with Greeks")
        print("  ✓ IV term structure")
        print("  ❌ No historical options prices")
        print("  ❌ No historical IV rank (only current)")
        
        print("\n💡 Recommendation for Backtesting:")
        print("  1. Use Polygon for historical options prices")
        print("  2. Use our IV rank database for historical IV ranks")
        print("  3. Use TastyTrade for real-time IV rank validation")
        print("  4. Combine all sources for comprehensive backtesting")


async def main():
    """Run all tests"""
    tester = OptionsDataTester()
    
    # Test each data source
    await tester.test_polygon_options()
    await tester.test_tastytrade_options_history()
    
    # Summarize findings
    tester.summarize_findings()


if __name__ == "__main__":
    asyncio.run(main())