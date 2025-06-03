"""
TastyTrade API integration for real IV rank data
Uses the official TastyTrade API v2
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class TastyTradeAPI:
    """Official TastyTrade API client for market data"""
    
    def __init__(self):
        self.base_url = "https://api.tastyworks.com"
        self.session = None
        self.auth_token = None
        self.username = os.getenv('TASTYTRADE_USERNAME')
        self.password = os.getenv('TASTYTRADE_PASSWORD')
        self.account = os.getenv('TASTYTRADE_ACCOUNT')
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def authenticate(self):
        """Authenticate with TastyTrade API"""
        auth_data = {
            "login": self.username,
            "password": self.password,
            "remember-me": True
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/sessions",
                json=auth_data
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    self.auth_token = data['data']['session-token']
                    logger.info("Successfully authenticated with TastyTrade")
                    return True
                else:
                    logger.error(f"Authentication failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def get_market_metrics(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get market metrics including IV rank for symbols
        
        Returns:
            Dict mapping symbol to metrics including iv_rank
        """
        if not self.auth_token:
            logger.error("Not authenticated")
            return {}
            
        headers = {
            "Authorization": self.auth_token
        }
        
        # TastyTrade uses different endpoint for market metrics
        results = {}
        
        for symbol in symbols:
            try:
                # Get option chain to calculate IV metrics
                async with self.session.get(
                    f"{self.base_url}/option-chains/{symbol}/nested",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract IV data from the response
                        iv_data = self._extract_iv_metrics(data)
                        results[symbol] = iv_data
                    else:
                        logger.warning(f"Failed to get data for {symbol}: {response.status}")
                        
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                
        return results
    
    def _extract_iv_metrics(self, chain_data: Dict) -> Dict:
        """Extract IV metrics from option chain data"""
        try:
            # TastyTrade provides these in the option chain response
            volatility_data = chain_data.get('data', {}).get('volatility', {})
            
            return {
                'implied_volatility': volatility_data.get('implied_volatility', 0),
                'iv_rank': volatility_data.get('iv_rank', 0),
                'iv_percentile': volatility_data.get('iv_percentile', 0),
                'historical_volatility_30': volatility_data.get('hv30', 0),
                'historical_volatility_60': volatility_data.get('hv60', 0),
                'iv_high_52w': volatility_data.get('iv_high_52w', 0),
                'iv_low_52w': volatility_data.get('iv_low_52w', 0)
            }
        except:
            return {}


class TastyTradeDataFetcher:
    """Fetcher specifically for backtesting with TastyTrade data"""
    
    def __init__(self):
        self.api = TastyTradeAPI()
        self._cache = {}  # Cache results to avoid repeated API calls
        
    async def get_iv_rank(self, symbol: str, date: datetime) -> float:
        """
        Get IV rank for a symbol on a specific date
        
        For backtesting, this will use current data as a proxy
        In production, you'd want historical data
        """
        
        # Check cache first
        cache_key = f"{symbol}_{date.strftime('%Y-%m-%d')}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            async with self.api as client:
                metrics = await client.get_market_metrics([symbol])
                
                if symbol in metrics and 'iv_rank' in metrics[symbol]:
                    iv_rank = metrics[symbol]['iv_rank']
                    
                    # Cache the result
                    self._cache[cache_key] = iv_rank
                    
                    return iv_rank
                    
        except Exception as e:
            logger.error(f"Error fetching IV rank: {e}")
            
        # Return None to indicate we should fall back to simulation
        return None
        
    async def get_full_metrics(self, symbol: str) -> Dict:
        """Get full volatility metrics for a symbol"""
        try:
            async with self.api as client:
                metrics = await client.get_market_metrics([symbol])
                return metrics.get(symbol, {})
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return {}


# Test function
async def test_tastytrade_connection():
    """Test TastyTrade API connection"""
    print("Testing TastyTrade API connection...")
    
    fetcher = TastyTradeDataFetcher()
    
    # Test getting IV rank for SPY
    iv_rank = await fetcher.get_iv_rank('SPY', datetime.now())
    
    if iv_rank is not None:
        print(f"✓ Successfully connected! SPY IV Rank: {iv_rank}")
        
        # Get full metrics
        metrics = await fetcher.get_full_metrics('SPY')
        print(f"Full metrics: {metrics}")
    else:
        print("✗ Failed to connect. Please check your credentials.")
        

if __name__ == "__main__":
    asyncio.run(test_tastytrade_connection())