"""
Polygon.io integration for historical options prices
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import os
import logging
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
logger = logging.getLogger(__name__)

class PolygonOptionsFetcher:
    """Fetch historical options data from Polygon.io"""
    
    def __init__(self):
        # Handle the typo in the env variable name
        self.api_key = os.getenv('POLYGON_API_KEY') or os.getenv('OLYGON_API_KEY')
        self.base_url = "https://api.polygon.io"
        self._cache = {}  # Cache to avoid repeated API calls
        
        if not self.api_key:
            logger.warning("No Polygon API key found - options prices will not be available")
        else:
            logger.info("Polygon API initialized for historical options data")
            
    async def get_options_chain(
        self, 
        symbol: str, 
        date: datetime,
        min_dte: int = 14,
        max_dte: int = 45
    ) -> Optional[Dict]:
        """
        Get historical options chain for a symbol on a specific date
        
        Returns dict with structure:
        {
            'expiration_date': {
                'calls': {strike: option_data},
                'puts': {strike: option_data}
            }
        }
        """
        if not self.api_key:
            return None
            
        # Check cache first
        cache_key = f"{symbol}_{date.strftime('%Y-%m-%d')}_{min_dte}_{max_dte}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            async with aiohttp.ClientSession() as session:
                # First, get available contracts
                contracts_url = f"{self.base_url}/v3/reference/options/contracts"
                params = {
                    'underlying_ticker': symbol,
                    'expired': 'false',
                    'expiration_date.gte': (date + timedelta(days=min_dte)).strftime('%Y-%m-%d'),
                    'expiration_date.lte': (date + timedelta(days=max_dte)).strftime('%Y-%m-%d'),
                    'limit': 1000,
                    'apiKey': self.api_key
                }
                
                async with session.get(contracts_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get contracts: {response.status}")
                        return None
                        
                    data = await response.json()
                    contracts = data.get('results', [])
                    
                    if not contracts:
                        logger.warning(f"No options contracts found for {symbol} on {date}")
                        return None
                        
                    # Organize contracts by expiration
                    options_by_expiry = {}
                    
                    for contract in contracts:
                        ticker = contract['ticker']
                        expiry = contract['expiration_date']
                        strike = contract['strike_price']
                        contract_type = contract['contract_type']
                        
                        if expiry not in options_by_expiry:
                            options_by_expiry[expiry] = {
                                'calls': {},
                                'puts': {},
                                'expiration': expiry,
                                'dte': (datetime.strptime(expiry, '%Y-%m-%d') - date).days
                            }
                        
                        # Get historical price for this option on the date
                        option_data = await self._get_option_price(ticker, date)
                        
                        if option_data:
                            option_info = {
                                'symbol': ticker,
                                'strike': strike,
                                **option_data
                            }
                            
                            if contract_type == 'call':
                                options_by_expiry[expiry]['calls'][strike] = option_info
                            else:
                                options_by_expiry[expiry]['puts'][strike] = option_info
                    
                    # Cache the result
                    self._cache[cache_key] = options_by_expiry
                    return options_by_expiry
                    
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return None
            
    async def _get_option_price(self, option_ticker: str, date: datetime) -> Optional[Dict]:
        """Get historical price for a specific option on a date"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get daily bar for the option
                date_str = date.strftime('%Y-%m-%d')
                url = f"{self.base_url}/v1/open-close/{option_ticker}/{date_str}"
                params = {'apiKey': self.api_key}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Calculate mid price
                        close = data.get('close', 0)
                        open_price = data.get('open', close)
                        high = data.get('high', close)
                        low = data.get('low', close)
                        
                        # Estimate bid/ask from high/low
                        spread = (high - low) * 0.5
                        mid = (high + low) / 2
                        
                        return {
                            'open': open_price,
                            'high': high,
                            'low': low,
                            'close': close,
                            'volume': data.get('volume', 0),
                            'bid': max(0, mid - spread/2),
                            'ask': mid + spread/2,
                            'mid': mid,
                            'has_trades': data.get('volume', 0) > 0
                        }
                    elif response.status == 404:
                        # No data for this date - option might not have traded
                        return None
                    else:
                        logger.warning(f"Failed to get price for {option_ticker}: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching option price: {e}")
            return None
            
    async def get_option_snapshot(self, symbol: str) -> Optional[Dict]:
        """
        Get current options snapshot with IV and Greeks
        Useful for validating historical data
        """
        if not self.api_key:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/v3/snapshot/options/{symbol}"
                params = {'apiKey': self.api_key}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        # Process snapshot data
                        snapshot = {}
                        for item in results:
                            details = item.get('details', {})
                            greeks = item.get('greeks', {})
                            
                            snapshot[details.get('ticker')] = {
                                'strike': details.get('strike_price'),
                                'expiration': details.get('expiration_date'),
                                'implied_volatility': item.get('implied_volatility'),
                                'bid': item.get('last_quote', {}).get('bid'),
                                'ask': item.get('last_quote', {}).get('ask'),
                                'delta': greeks.get('delta'),
                                'gamma': greeks.get('gamma'),
                                'theta': greeks.get('theta'),
                                'vega': greeks.get('vega')
                            }
                            
                        return snapshot
                    else:
                        logger.error(f"Failed to get snapshot: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching snapshot: {e}")
            return None
            
    async def get_historical_iv(
        self, 
        symbol: str, 
        date: datetime,
        dte_target: int = 30
    ) -> Optional[float]:
        """
        Calculate approximate IV from historical options prices
        Uses ATM options around target DTE
        """
        # Get options chain
        chain = await self.get_options_chain(symbol, date, dte_target-10, dte_target+10)
        
        if not chain:
            return None
            
        # Find expiration closest to target DTE
        best_expiry = None
        best_dte_diff = float('inf')
        
        for expiry, data in chain.items():
            dte_diff = abs(data['dte'] - dte_target)
            if dte_diff < best_dte_diff:
                best_dte_diff = dte_diff
                best_expiry = expiry
                
        if not best_expiry:
            return None
            
        # Get ATM options
        expiry_data = chain[best_expiry]
        
        # Need current price to find ATM
        # This would come from stock data
        # For now, return None - IV will come from our database
        return None


# Test function
async def test_polygon_fetcher():
    """Test Polygon options data fetching"""
    print("Testing Polygon Options Fetcher...")
    
    fetcher = PolygonOptionsFetcher()
    
    if not fetcher.api_key:
        print("❌ No Polygon API key found")
        return
        
    # Test dates
    test_cases = [
        ('SPY', datetime(2024, 11, 1)),   # Recent date
        ('QQQ', datetime(2024, 10, 15)),  # Mid-month
    ]
    
    for symbol, date in test_cases:
        print(f"\n{symbol} on {date.strftime('%Y-%m-%d')}:")
        
        # Get options chain
        chain = await fetcher.get_options_chain(symbol, date)
        
        if chain:
            print(f"  ✓ Found {len(chain)} expirations")
            
            # Show first expiration
            first_expiry = list(chain.keys())[0]
            expiry_data = chain[first_expiry]
            
            print(f"  First expiration: {first_expiry} ({expiry_data['dte']} DTE)")
            print(f"    Calls: {len(expiry_data['calls'])} strikes")
            print(f"    Puts: {len(expiry_data['puts'])} strikes")
            
            # Show sample call
            if expiry_data['calls']:
                strike = list(expiry_data['calls'].keys())[0]
                call = expiry_data['calls'][strike]
                print(f"    Sample call ({strike} strike):")
                print(f"      Mid: ${call.get('mid', 0):.2f}")
                print(f"      Volume: {call.get('volume', 0)}")
        else:
            print("  ❌ No options data available")
            
    # Test snapshot
    print("\n\nTesting current snapshot:")
    snapshot = await fetcher.get_option_snapshot('SPY')
    
    if snapshot:
        print(f"  ✓ Got snapshot with {len(snapshot)} options")
        # Show first option with Greeks
        for ticker, data in list(snapshot.items())[:1]:
            if data.get('delta'):
                print(f"  Sample option {ticker}:")
                print(f"    IV: {data.get('implied_volatility', 0):.1%}")
                print(f"    Delta: {data.get('delta', 0):.3f}")
                print(f"    Theta: {data.get('theta', 0):.3f}")
                break
    else:
        print("  ℹ️  Snapshot requires paid Polygon subscription")


if __name__ == "__main__":
    asyncio.run(test_polygon_fetcher())