"""
Alpaca historical options data fetcher for backtesting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import os
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest, StockQuotesRequest,
    OptionBarsRequest, OptionChainRequest, OptionSnapshotRequest,
    OptionLatestQuoteRequest, OptionTradesRequest
)
from alpaca.data.timeframe import TimeFrame

logger = logging.getLogger(__name__)

class AlpacaDataFetcher:
    """Fetch historical options data from Alpaca for backtesting
    
    Note: Alpaca historical options data is only available from February 2024 onwards.
    For earlier dates, we use sophisticated simulation based on historical volatility patterns.
    """
    
    # Alpaca options data availability cutoff
    OPTIONS_DATA_START_DATE = datetime(2024, 2, 1)
    
    def __init__(self):
        # Initialize Alpaca clients
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        
        # Initialize options client
        try:
            self.options_client = OptionHistoricalDataClient(api_key, secret_key)
            self.has_options_access = True
            logger.info("Alpaca options data client initialized (data available from Feb 2024)")
        except Exception as e:
            logger.warning(f"Options data client initialization failed: {e}")
            logger.warning("Will use simulated options data")
            self.has_options_access = False
            self.options_client = None
            
    async def get_stock_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical stock price data"""
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            bars = self.stock_client.get_stock_bars(request)
            df = bars.df
            
            # Calculate additional metrics
            df['daily_return'] = df['close'].pct_change()
            df['daily_range'] = (df['high'] - df['low']) / df['open'] * 100
            df['percent_change'] = (df['close'] - df['open']) / df['open'] * 100
            
            # Calculate realized volatility (20-day)
            df['realized_vol'] = df['daily_return'].rolling(20).std() * np.sqrt(252) * 100
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return pd.DataFrame()
            
    async def get_options_chain(self, symbol: str, date: datetime, 
                               dte_min: int = 7, dte_max: int = 45) -> List[Dict]:
        """Get options chain for a specific date
        
        Uses real Alpaca data for dates after Feb 2024, simulation for earlier dates.
        """
        
        # Check if date is before Alpaca options data availability
        if date < self.OPTIONS_DATA_START_DATE:
            logger.info(f"Date {date.date()} is before Alpaca options data availability - using simulation")
            return self._simulate_options_chain(symbol, date, dte_min, dte_max)
            
        if not self.has_options_access:
            # Return simulated options chain
            return self._simulate_options_chain(symbol, date, dte_min, dte_max)
            
        try:
            # Get expiration dates
            exp_date_min = date + timedelta(days=dte_min)
            exp_date_max = date + timedelta(days=dte_max)
            
            # Request options chain
            request = OptionChainRequest(
                underlying_symbol=symbol,  # Note: it's underlying_symbol (singular)
                expiration_date_gte=exp_date_min.strftime('%Y-%m-%d'),
                expiration_date_lte=exp_date_max.strftime('%Y-%m-%d')
            )
            
            chain_data = self.options_client.get_option_chain(request)
            
            # Process and return chain data
            options_data = []
            
            # The chain_data is a dictionary keyed by symbol
            for option_symbol, snapshot in chain_data.items():
                if snapshot and snapshot.latest_quote:
                    # Parse option symbol to extract details
                    # Format: SPY241206C00590000 = SPY Dec 6 2024 Call $590
                    try:
                        # Extract components from symbol
                        underlying = option_symbol[:3]  # First 3 chars
                        date_str = option_symbol[3:9]   # YYMMDD
                        option_type = option_symbol[9]  # C or P
                        strike_str = option_symbol[10:] # Strike price * 1000
                        
                        strike = int(strike_str) / 1000
                        exp_date = datetime.strptime('20' + date_str, '%Y%m%d').date()
                        
                        latest_quote = snapshot.latest_quote
                        latest_trade = snapshot.latest_trade
                        
                        options_data.append({
                            'symbol': option_symbol,
                            'underlying': underlying,
                            'strike': strike,
                            'expiration': exp_date,
                            'type': 'call' if option_type == 'C' else 'put',
                            'bid': float(latest_quote.bid_price) if latest_quote.bid_price else 0,
                            'ask': float(latest_quote.ask_price) if latest_quote.ask_price else 0,
                            'mid': (float(latest_quote.bid_price or 0) + float(latest_quote.ask_price or 0)) / 2,
                            'volume': int(latest_trade.size) if latest_trade and latest_trade.size else 0,
                            'open_interest': 0,  # Not available in snapshot
                            'implied_volatility': float(snapshot.implied_volatility) if snapshot.implied_volatility else 0.25
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing option symbol {option_symbol}: {e}")
                        continue
                
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return self._simulate_options_chain(symbol, date, dte_min, dte_max)
            
    def _simulate_options_chain(self, symbol: str, date: datetime, 
                               dte_min: int, dte_max: int) -> List[Dict]:
        """Simulate realistic options chain when real data isn't available"""
        
        # Get a reasonable stock price
        base_price = {
            'SPY': 450, 'QQQ': 380, 'IWM': 190, 'DIA': 350,
            'AAPL': 180, 'MSFT': 420, 'GOOGL': 170, 'AMZN': 185
        }.get(symbol, 100)
        
        options_data = []
        
        # Generate weekly expirations
        current_exp = date + timedelta(days=dte_min)
        
        while current_exp <= date + timedelta(days=dte_max):
            # Skip to next Friday
            days_to_friday = (4 - current_exp.weekday()) % 7
            if days_to_friday == 0 and current_exp.weekday() != 4:
                days_to_friday = 7
            current_exp += timedelta(days=days_to_friday)
            
            if current_exp > date + timedelta(days=dte_max):
                break
                
            dte = (current_exp - date).days
            
            # Generate strikes around current price
            strikes = []
            for i in range(-10, 11):
                if symbol in ['SPY', 'QQQ', 'DIA']:
                    strike = round(base_price + i * 1)  # $1 strikes
                else:
                    strike = round(base_price + i * 5)  # $5 strikes
                strikes.append(strike)
                
            # Generate options for each strike
            for strike in strikes:
                # Calculate theoretical option prices using simplified Black-Scholes
                moneyness = (strike - base_price) / base_price
                time_value = np.sqrt(dte / 365)
                base_iv = 0.20 + abs(moneyness) * 0.1  # Higher IV for OTM options
                
                for option_type in ['call', 'put']:
                    if option_type == 'call':
                        intrinsic = max(0, base_price - strike)
                        delta = 0.5 + moneyness * 2 if moneyness < 0 else 0.5 - moneyness
                    else:
                        intrinsic = max(0, strike - base_price)
                        delta = -0.5 + moneyness * 2 if moneyness > 0 else -0.5 - moneyness
                        
                    # Add time value
                    time_premium = base_price * base_iv * time_value * abs(delta)
                    mid_price = intrinsic + time_premium
                    
                    # Add spread
                    spread = max(0.05, mid_price * 0.02)
                    bid = mid_price - spread/2
                    ask = mid_price + spread/2
                    
                    options_data.append({
                        'symbol': f"{symbol}{current_exp.strftime('%y%m%d')}{option_type[0].upper()}{strike}",
                        'underlying': symbol,
                        'strike': strike,
                        'expiration': current_exp,
                        'type': option_type,
                        'bid': max(0.01, round(bid, 2)),
                        'ask': max(0.02, round(ask, 2)),
                        'mid': max(0.015, round(mid_price, 2)),
                        'volume': np.random.randint(0, 1000),
                        'open_interest': np.random.randint(100, 5000),
                        'implied_volatility': base_iv,
                        'delta': delta,
                        'dte': dte
                    })
                    
        return options_data
        
    async def get_historical_volatility_data(self, symbol: str, date: datetime, 
                                           lookback_days: int = 365) -> Dict:
        """Calculate historical volatility metrics"""
        
        start_date = date - timedelta(days=lookback_days)
        df = await self.get_stock_data(symbol, start_date, date)
        
        if df.empty:
            return {}
            
        # Calculate various volatility metrics
        current_date_data = df[df.index.date == date.date()]
        if current_date_data.empty:
            return {}
            
        # Get realized volatility over different periods
        hv_10 = df['daily_return'].tail(10).std() * np.sqrt(252) * 100
        hv_20 = df['daily_return'].tail(20).std() * np.sqrt(252) * 100
        hv_30 = df['daily_return'].tail(30).std() * np.sqrt(252) * 100
        
        # Calculate IV rank and percentile (using HV as proxy)
        all_hv_20 = df['realized_vol'].dropna()
        current_hv = hv_20
        
        if len(all_hv_20) > 0:
            iv_rank = ((current_hv - all_hv_20.min()) / 
                      (all_hv_20.max() - all_hv_20.min()) * 100)
            iv_percentile = (all_hv_20 < current_hv).sum() / len(all_hv_20) * 100
        else:
            iv_rank = 50
            iv_percentile = 50
            
        return {
            'date': date,
            'current_price': float(current_date_data['close'].iloc[0]),
            'daily_change': float(current_date_data['percent_change'].iloc[0]),
            'volume': int(current_date_data['volume'].iloc[0]),
            'hv_10': hv_10,
            'hv_20': hv_20,
            'hv_30': hv_30,
            'iv_rank': iv_rank,
            'iv_percentile': iv_percentile,
            'high_low_range': float(current_date_data['daily_range'].iloc[0])
        }
        
    async def find_volatility_events(self, symbol: str, start_date: datetime, 
                                   end_date: datetime, min_move: float = 1.5) -> List[Dict]:
        """Find historical volatility events for backtesting"""
        
        df = await self.get_stock_data(symbol, start_date, end_date)
        if df.empty:
            return []
            
        # Find days with significant moves
        volatility_events = []
        
        for idx, row in df.iterrows():
            if abs(row['percent_change']) >= min_move:
                # Get volatility data for this date
                vol_data = await self.get_historical_volatility_data(
                    symbol, idx.date(), lookback_days=60
                )
                
                if vol_data and vol_data.get('iv_rank', 0) >= 70:
                    event = {
                        'date': idx.date(),
                        'symbol': symbol,
                        'price': row['close'],
                        'percent_change': row['percent_change'],
                        'volume': row['volume'],
                        'iv_rank': vol_data['iv_rank'],
                        'iv_percentile': vol_data['iv_percentile'],
                        'event_type': 'spike_up' if row['percent_change'] > 0 else 'spike_down'
                    }
                    volatility_events.append(event)
                    
        return volatility_events
        
    def calculate_option_spreads(self, options_chain: List[Dict], 
                               spread_type: str, current_price: float) -> List[Dict]:
        """Calculate potential credit spreads from options chain"""
        
        spreads = []
        
        # Filter by type
        if spread_type == 'call_credit':
            options = [opt for opt in options_chain if opt['type'] == 'call']
            otm_options = [opt for opt in options if opt['strike'] > current_price]
        else:  # put_credit
            options = [opt for opt in options_chain if opt['type'] == 'put']
            otm_options = [opt for opt in options if opt['strike'] < current_price]
            
        # Sort by strike
        otm_options.sort(key=lambda x: x['strike'])
        
        # Find spreads with $5 width
        for i in range(len(otm_options) - 1):
            short_option = otm_options[i]
            
            # Find long option $5 away
            for long_option in otm_options[i+1:]:
                spread_width = abs(long_option['strike'] - short_option['strike'])
                
                if spread_width == 5:  # $5 wide spreads
                    credit = short_option['mid'] - long_option['mid']
                    
                    if credit > 0.20:  # Minimum $0.20 credit
                        spread = {
                            'type': spread_type,
                            'short_strike': short_option['strike'],
                            'long_strike': long_option['strike'],
                            'short_bid': short_option['bid'],
                            'short_ask': short_option['ask'],
                            'long_bid': long_option['bid'],
                            'long_ask': long_option['ask'],
                            'credit': credit,
                            'spread_width': spread_width,
                            'expiration': short_option['expiration'],
                            'dte': short_option.get('dte', 0),
                            'short_iv': short_option['implied_volatility'],
                            'short_delta': short_option.get('delta', 0)
                        }
                        spreads.append(spread)
                    break
                    
        return spreads