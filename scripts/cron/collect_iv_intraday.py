#!/usr/bin/env python3
"""
Intraday IV Data Collector
Collects IV data multiple times during market hours for more accurate tracking.
Designed to run every 30 minutes via cron during market hours.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import sqlite3
import logging
from datetime import datetime, time
import yfinance as yf
from typing import Dict, List, Optional
import pytz

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'intraday_iv_collector.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntradayIVCollector:
    """Collects IV data during market hours."""
    
    def __init__(self, db_path: str = 'historical_iv.db'):
        self.db_path = db_path
        self.symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLE', 'XLF', 'XLK', 'GLD', 'TLT']
        self.eastern = pytz.timezone('US/Eastern')
        self.setup_database()
        
    def setup_database(self):
        """Ensure intraday table exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create intraday IV table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intraday_iv (
                symbol VARCHAR(10),
                date DATE,
                time TIME,
                iv_30d FLOAT,
                atm_call_iv FLOAT,
                atm_put_iv FLOAT,
                underlying_price FLOAT,
                bid_ask_spread FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date, time)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def is_market_hours(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now(self.eastern)
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
            
        # Check time
        current_time = now.time()
        return market_open <= current_time <= market_close
    
    def get_current_iv(self, symbol: str) -> Optional[Dict]:
        """Get current IV from options chain."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current price
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not current_price:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    return None
            
            # Get options
            expirations = ticker.options
            if not expirations:
                return None
            
            # Find expiration closest to 30 days
            today = datetime.now()
            target_days = 30
            best_exp = None
            min_diff = float('inf')
            
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days_diff = abs((exp_date - today).days - target_days)
                if days_diff < min_diff:
                    min_diff = days_diff
                    best_exp = exp
            
            if not best_exp:
                return None
            
            # Get option chain
            opt_chain = ticker.option_chain(best_exp)
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            if calls.empty or puts.empty:
                return None
            
            # Find ATM options
            call_strikes = calls['strike'].values
            put_strikes = puts['strike'].values
            
            # Find closest strikes to current price
            atm_call_idx = abs(call_strikes - current_price).argmin()
            atm_put_idx = abs(put_strikes - current_price).argmin()
            
            atm_call = calls.iloc[atm_call_idx]
            atm_put = puts.iloc[atm_put_idx]
            
            # Get IVs
            call_iv = atm_call['impliedVolatility']
            put_iv = atm_put['impliedVolatility']
            
            # Calculate bid-ask spread as quality indicator
            call_spread = (atm_call['ask'] - atm_call['bid']) / atm_call['lastPrice'] if atm_call['lastPrice'] > 0 else 0
            put_spread = (atm_put['ask'] - atm_put['bid']) / atm_put['lastPrice'] if atm_put['lastPrice'] > 0 else 0
            avg_spread = (call_spread + put_spread) / 2
            
            # Average IV
            avg_iv = (call_iv + put_iv) / 2
            
            return {
                'iv_30d': avg_iv,
                'call_iv': call_iv,
                'put_iv': put_iv,
                'underlying_price': current_price,
                'bid_ask_spread': avg_spread
            }
            
        except Exception as e:
            logger.error(f"Error getting IV for {symbol}: {e}")
            return None
    
    def collect_and_store(self):
        """Collect IV data for all symbols and store."""
        if not self.is_market_hours():
            logger.info("Market is closed, skipping collection")
            return
        
        logger.info(f"Starting intraday IV collection for {len(self.symbols)} symbols")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        
        success_count = 0
        
        for symbol in self.symbols:
            try:
                iv_data = self.get_current_iv(symbol)
                
                if iv_data and iv_data['iv_30d'] > 0:
                    # Store intraday data
                    cursor.execute("""
                        INSERT OR REPLACE INTO intraday_iv 
                        (symbol, date, time, iv_30d, atm_call_iv, atm_put_iv, 
                         underlying_price, bid_ask_spread)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        current_date,
                        current_time,
                        iv_data['iv_30d'],
                        iv_data['call_iv'],
                        iv_data['put_iv'],
                        iv_data['underlying_price'],
                        iv_data['bid_ask_spread']
                    ))
                    
                    # Also update main historical_iv table with latest
                    cursor.execute("""
                        INSERT OR REPLACE INTO historical_iv 
                        (symbol, date, iv_30d, iv_60d, iv_90d, underlying_price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        current_date,
                        iv_data['iv_30d'],
                        iv_data['iv_30d'],  # Use 30d as proxy
                        iv_data['iv_30d'],  # Use 30d as proxy
                        iv_data['underlying_price']
                    ))
                    
                    success_count += 1
                    logger.info(f"✓ {symbol}: IV={iv_data['iv_30d']*100:.1f}%, "
                              f"Price=${iv_data['underlying_price']:.2f}")
                else:
                    logger.warning(f"✗ {symbol}: No IV data available")
                    
            except Exception as e:
                logger.error(f"Error collecting {symbol}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Intraday collection complete: {success_count}/{len(self.symbols)} successful")
        
        # Calculate and log IV ranks for key symbols
        self.log_current_ranks()
    
    def log_current_ranks(self):
        """Log current IV ranks for monitoring."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            for symbol in ['SPY', 'QQQ']:
                # Get 30-day min/max
                query = """
                    SELECT MIN(iv_30d) as min_iv, MAX(iv_30d) as max_iv,
                           (SELECT iv_30d FROM historical_iv 
                            WHERE symbol = ? ORDER BY date DESC LIMIT 1) as current_iv
                    FROM historical_iv
                    WHERE symbol = ?
                    AND date >= date('now', '-30 days')
                    AND iv_30d > 0
                """
                
                result = conn.execute(query, (symbol, symbol)).fetchone()
                
                if result and result[2]:  # current_iv exists
                    min_iv, max_iv, current_iv = result
                    if max_iv > min_iv:
                        iv_rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100
                        logger.info(f"{symbol} 30-day IV Rank: {iv_rank:.1f}% "
                                  f"(Current: {current_iv*100:.1f}%, "
                                  f"Range: {min_iv*100:.1f}%-{max_iv*100:.1f}%)")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error calculating ranks: {e}")

def main():
    """Main function."""
    collector = IntradayIVCollector()
    collector.collect_and_store()

if __name__ == "__main__":
    main()