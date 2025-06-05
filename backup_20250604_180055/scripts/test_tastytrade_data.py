"""
Test script to explore TastyTrade API and see what options data is available
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

class TastyTradeExplorer:
    """Explore TastyTrade API endpoints and data"""
    
    def __init__(self):
        # TastyTrade API endpoints
        self.base_url = "https://api.tastyworks.com"
        self.sandbox_url = "https://api.cert.tastyworks.com"  # Sandbox for testing
        self.session_token = None
        self.username = os.getenv('TASTYTRADE_USERNAME')
        self.password = os.getenv('TASTYTRADE_PASSWORD')
        
    async def test_connection(self):
        """Test basic connection to TastyTrade"""
        print("\n=== Testing TastyTrade Connection ===")
        
        # Test both production and sandbox URLs
        for name, url in [("Production", self.base_url), ("Sandbox", self.sandbox_url)]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/") as response:
                        print(f"\n{name} API ({url}):")
                        print(f"  Status: {response.status}")
                        if response.status == 200:
                            print("  ✓ API is reachable")
                        else:
                            print("  ✗ API returned non-200 status")
            except Exception as e:
                print(f"  ✗ Connection failed: {e}")
                
    async def explore_public_endpoints(self):
        """Explore what endpoints are available without authentication"""
        print("\n=== Exploring Public Endpoints ===")
        
        public_endpoints = [
            "/symbols/search/SPY",
            "/public-watchlists",
            "/quote-streamer-tokens",
            "/market-metrics",
            "/instruments/equity-options",
            "/option-chains/SPY",
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in public_endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    async with session.get(url) as response:
                        print(f"\n{endpoint}:")
                        print(f"  Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            print(f"  Response preview: {json.dumps(data, indent=2)[:200]}...")
                        elif response.status == 401:
                            print("  → Requires authentication")
                        else:
                            text = await response.text()
                            print(f"  Response: {text[:100]}")
                            
                except Exception as e:
                    print(f"  Error: {e}")
                    
    async def test_authentication(self):
        """Test authentication with provided credentials"""
        if not self.username or not self.password:
            print("\n=== Authentication Test ===")
            print("✗ No credentials found in .env file")
            print("  Please add TASTYTRADE_USERNAME and TASTYTRADE_PASSWORD")
            return False
            
        print("\n=== Testing Authentication ===")
        
        auth_data = {
            "login": self.username,
            "password": self.password,
            "remember-me": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/sessions",
                    json=auth_data
                ) as response:
                    print(f"Authentication status: {response.status}")
                    
                    if response.status == 201:
                        data = await response.json()
                        self.session_token = data['data']['session-token']
                        print("✓ Authentication successful!")
                        print(f"  Session token: {self.session_token[:20]}...")
                        return True
                    else:
                        text = await response.text()
                        print(f"✗ Authentication failed: {text}")
                        return False
                        
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
            
    async def explore_authenticated_data(self):
        """Explore data available with authentication"""
        if not self.session_token:
            print("\n=== Authenticated Data ===")
            print("✗ Not authenticated, skipping...")
            return
            
        print("\n=== Exploring Authenticated Data ===")
        
        headers = {"Authorization": self.session_token}
        
        # Endpoints to test
        endpoints = [
            "/accounts",
            "/margin-requirements",
            "/market-metrics?symbols=SPY,QQQ,IWM",
            "/instruments/equity-options?symbol[]=SPY",
            "/option-chains/SPY/nested",
            f"/option-chains/SPY/expirations",
            "/market-metrics/historic-volatility?symbols=SPY",
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    async with session.get(url, headers=headers) as response:
                        print(f"\n{endpoint}:")
                        print(f"  Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            # Pretty print with better formatting
                            if 'data' in data:
                                self._print_data_structure(data['data'])
                            else:
                                print(f"  Data: {json.dumps(data, indent=2)[:300]}...")
                                
                except Exception as e:
                    print(f"  Error: {e}")
                    
    def _print_data_structure(self, data):
        """Pretty print data structure"""
        if isinstance(data, list) and len(data) > 0:
            print(f"  List with {len(data)} items")
            print(f"  First item structure:")
            self._print_dict_structure(data[0], indent=4)
        elif isinstance(data, dict):
            self._print_dict_structure(data, indent=2)
        else:
            print(f"  Type: {type(data)}")
            
    def _print_dict_structure(self, d, indent=0):
        """Print dictionary structure"""
        if not isinstance(d, dict):
            return
            
        for key, value in d.items():
            spaces = " " * indent
            if isinstance(value, dict):
                print(f"{spaces}{key}: <dict>")
                self._print_dict_structure(value, indent + 2)
            elif isinstance(value, list):
                if len(value) > 0:
                    print(f"{spaces}{key}: <list of {len(value)} items>")
                else:
                    print(f"{spaces}{key}: <empty list>")
            else:
                print(f"{spaces}{key}: {value}")
                
    async def test_options_chain_data(self):
        """Test specific options chain data retrieval"""
        if not self.session_token:
            return
            
        print("\n=== Testing Options Chain Data ===")
        
        headers = {"Authorization": self.session_token}
        symbol = "SPY"
        
        async with aiohttp.ClientSession() as session:
            # Get expirations
            exp_url = f"{self.base_url}/option-chains/{symbol}/expirations"
            async with session.get(exp_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    expirations = data.get('data', {}).get('expirations', [])
                    
                    print(f"\nAvailable expirations for {symbol}:")
                    for i, exp in enumerate(expirations[:5]):  # Show first 5
                        print(f"  {i+1}. {exp}")
                        
                    # Get chain for first expiration
                    if expirations:
                        first_exp = expirations[0]
                        chain_url = f"{self.base_url}/option-chains/{symbol}/nested?expiration={first_exp}"
                        
                        async with session.get(chain_url, headers=headers) as chain_response:
                            if chain_response.status == 200:
                                chain_data = await chain_response.json()
                                
                                print(f"\nOption chain for {first_exp}:")
                                self._analyze_chain_data(chain_data)
                                
    def _analyze_chain_data(self, chain_data):
        """Analyze option chain data structure"""
        if 'data' in chain_data and 'items' in chain_data['data']:
            items = chain_data['data']['items']
            
            if items:
                print(f"  Total strikes: {len(items)}")
                
                # Look at first strike
                first_strike = items[0]
                print(f"\n  Sample strike data structure:")
                
                # Check what fields are available
                fields = list(first_strike.keys())
                print(f"  Available fields: {', '.join(fields)}")
                
                # Look for IV data
                iv_fields = [f for f in fields if 'iv' in f.lower() or 'impl' in f.lower() or 'vol' in f.lower()]
                if iv_fields:
                    print(f"\n  Volatility-related fields found:")
                    for field in iv_fields:
                        print(f"    {field}: {first_strike.get(field)}")
                        
    async def test_market_metrics(self):
        """Test market metrics endpoint specifically for IV data"""
        if not self.session_token:
            return
            
        print("\n=== Testing Market Metrics (IV Data) ===")
        
        headers = {"Authorization": self.session_token}
        symbols = ["SPY", "QQQ", "IWM"]
        
        # Try different metric endpoints
        metric_endpoints = [
            f"/market-metrics?symbols={','.join(symbols)}",
            f"/market-metrics/volatility?symbols={','.join(symbols)}",
            f"/market-metrics/iv-rank?symbols={','.join(symbols)}",
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in metric_endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    async with session.get(url, headers=headers) as response:
                        print(f"\n{endpoint}:")
                        print(f"  Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and 'items' in data['data']:
                                for item in data['data']['items']:
                                    symbol = item.get('symbol', 'Unknown')
                                    print(f"\n  {symbol}:")
                                    
                                    # Look for IV-related fields
                                    for key, value in item.items():
                                        if any(term in key.lower() for term in ['iv', 'implied', 'volatility', 'rank']):
                                            print(f"    {key}: {value}")
                                            
                except Exception as e:
                    print(f"  Error: {e}")


async def main():
    """Run all tests"""
    explorer = TastyTradeExplorer()
    
    # Test connection first
    await explorer.test_connection()
    
    # Explore public endpoints
    await explorer.explore_public_endpoints()
    
    # Test authentication
    authenticated = await explorer.test_authentication()
    
    if authenticated:
        # Explore authenticated endpoints
        await explorer.explore_authenticated_data()
        
        # Test specific options data
        await explorer.test_options_chain_data()
        
        # Test market metrics
        await explorer.test_market_metrics()
    
    print("\n=== Summary ===")
    print("Based on the tests above, we can determine what data TastyTrade provides.")
    print("Look for IV rank, IV percentile, and historical volatility data in the responses.")


if __name__ == "__main__":
    # First check if we have credentials
    if not os.getenv('TASTYTRADE_USERNAME'):
        print("=" * 60)
        print("TASTYTRADE CREDENTIALS NOT FOUND")
        print("=" * 60)
        print("\nTo test TastyTrade data access, please:")
        print("1. Sign up for a free TastyTrade account at https://tastyworks.com")
        print("2. Add to your .env file:")
        print("   TASTYTRADE_USERNAME=your_username")
        print("   TASTYTRADE_PASSWORD=your_password")
        print("\nWe'll still test public endpoints...\n")
    
    asyncio.run(main())