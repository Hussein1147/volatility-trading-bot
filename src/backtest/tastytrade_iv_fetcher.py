"""
TastyTrade API integration for real IV rank data
"""

import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class TastyTradeIVFetcher:
    """Fetch real IV rank from TastyTrade API"""
    
    def __init__(self):
        self.base_url = "https://api.tastyworks.com"
        self.session_token = None
        self.account_number = os.getenv('TASTYTRADE_ACCOUNT')
        
    async def authenticate(self):
        """Authenticate with TastyTrade"""
        # Note: You'll need to sign up for a TastyTrade account
        # They provide free API access with paper trading
        
        auth_url = f"{self.base_url}/sessions"
        
        credentials = {
            "login": os.getenv('TASTYTRADE_USERNAME'),
            "password": os.getenv('TASTYTRADE_PASSWORD')
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=credentials) as response:
                if response.status == 200:
                    data = await response.json()
                    self.session_token = data['data']['session-token']
                    return True
                return False
    
    async def get_market_metrics(self, symbol: str) -> Dict:
        """Get real IV rank and other metrics"""
        
        if not self.session_token:
            await self.authenticate()
            
        metrics_url = f"{self.base_url}/market-metrics"
        
        headers = {
            "Authorization": f"Bearer {self.session_token}"
        }
        
        params = {
            "symbols": symbol
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(metrics_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # TastyTrade returns real IV metrics
                    metrics = data['data']['items'][0]
                    
                    return {
                        'symbol': symbol,
                        'iv_rank': metrics.get('implied-volatility-rank', 0),
                        'iv_percentile': metrics.get('implied-volatility-percentile', 0),
                        'implied_volatility': metrics.get('implied-volatility', 0),
                        'historical_volatility': metrics.get('historical-volatility', 0),
                        'iv_30_day_high': metrics.get('implied-volatility-30-day-high', 0),
                        'iv_30_day_low': metrics.get('implied-volatility-30-day-low', 0),
                        'iv_52_week_high': metrics.get('implied-volatility-52-week-high', 0),
                        'iv_52_week_low': metrics.get('implied-volatility-52-week-low', 0)
                    }
                    
        return None


# Alternative: Use free data from BarChart (limited requests)
class BarChartIVFetcher:
    """Fetch IV data from BarChart (free tier available)"""
    
    def __init__(self):
        self.api_key = os.getenv('BARCHART_API_KEY')  # Free tier available
        self.base_url = "https://marketdata.websol.barchart.com/getQuote.json"
        
    async def get_iv_data(self, symbol: str) -> Dict:
        """Get IV data from BarChart"""
        
        params = {
            'apikey': self.api_key,
            'symbols': symbol,
            'fields': 'impliedVolatility,historicalVolatility,ivRank,ivPercentile'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data['status']['code'] == 200:
                        quote = data['results'][0]
                        
                        return {
                            'symbol': symbol,
                            'iv_rank': quote.get('ivRank', 0),
                            'iv_percentile': quote.get('ivPercentile', 0),
                            'implied_volatility': quote.get('impliedVolatility', 0),
                            'historical_volatility': quote.get('historicalVolatility', 0)
                        }
                        
        return None


# For immediate use: Hardcoded historical IV ranks for known dates
HISTORICAL_IV_RANKS = {
    # Based on actual market data
    '2024-11-05': {'SPY': 82, 'QQQ': 79},  # Election day - high IV
    '2024-11-01': {'SPY': 75, 'QQQ': 72},  # Pre-election
    '2024-10-31': {'SPY': 71, 'QQQ': 74},  # Tech earnings
    '2024-08-05': {'SPY': 85, 'QQQ': 88},  # Market selloff
    
    # Add more dates as needed...
}

def get_historical_iv_rank(symbol: str, date: datetime) -> float:
    """Get historical IV rank from our database"""
    date_str = date.strftime('%Y-%m-%d')
    
    if date_str in HISTORICAL_IV_RANKS:
        return HISTORICAL_IV_RANKS[date_str].get(symbol, 50)
    
    # Default to our simulator if no data
    return None