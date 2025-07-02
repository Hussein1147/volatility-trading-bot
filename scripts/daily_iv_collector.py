#!/usr/bin/env python3
"""
Daily IV Data Collector
Collects and stores IV data from multiple sources to build historical database.
Designed to be run daily via cron job.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Optional
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_iv_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyIVCollector:
    """Collects IV data daily from multiple sources."""
    
    def __init__(self, db_path: str = 'historical_iv.db'):
        self.db_path = db_path
        self.symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLE', 'XLF', 'XLK', 'GLD', 'TLT']
        self.setup_database()
        
    def setup_database(self):
        """Ensure database tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main historical IV table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_iv (
                symbol VARCHAR(10),
                date DATE,
                iv_30d FLOAT,
                iv_60d FLOAT,
                iv_90d FLOAT,
                atm_iv_call FLOAT,
                atm_iv_put FLOAT,
                iv_skew FLOAT,
                underlying_price FLOAT,
                volume INTEGER,
                data_points INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # Daily collection status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iv_collection_log (
                date DATE,
                symbol TEXT,
                status TEXT,
                iv_30d FLOAT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def collect_yahoo_iv(self, symbol: str) -> Optional[Dict]:
        """Collect current IV from Yahoo Finance options chain."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current price
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            
            if not current_price:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    
            # Get options expirations
            expirations = ticker.options
            
            if not expirations:
                raise ValueError(f"No options data available for {symbol}")
                
            # Find expiration closest to 30 days
            today = datetime.now()
            target_date = today + timedelta(days=30)
            
            best_exp = None
            min_diff = float('inf')
            
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                diff = abs((exp_date - target_date).days)
                if diff < min_diff:
                    min_diff = diff
                    best_exp = exp_str
                    
            if not best_exp:
                raise ValueError(f"No suitable expiration found for {symbol}")
                
            # Get option chain
            opt_chain = ticker.option_chain(best_exp)
            
            # Find ATM options
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            # Get ATM strike
            atm_call_idx = calls['strike'].sub(current_price).abs().idxmin()
            atm_put_idx = puts['strike'].sub(current_price).abs().idxmin()
            
            # Get IVs
            call_iv = calls.loc[atm_call_idx, 'impliedVolatility']
            put_iv = puts.loc[atm_put_idx, 'impliedVolatility']
            
            # Average
            avg_iv = (call_iv + put_iv) / 2
            
            # Calculate skew (25 delta put - 25 delta call)
            try:
                # Find 25 delta options (approximation)
                otm_put_strike = current_price * 0.95  # ~25 delta put
                otm_call_strike = current_price * 1.05  # ~25 delta call
                
                otm_put_idx = puts['strike'].sub(otm_put_strike).abs().idxmin()
                otm_call_idx = calls['strike'].sub(otm_call_strike).abs().idxmin()
                
                otm_put_iv = puts.loc[otm_put_idx, 'impliedVolatility']
                otm_call_iv = calls.loc[otm_call_idx, 'impliedVolatility']
                
                iv_skew = otm_put_iv - otm_call_iv
            except:
                iv_skew = 0.0
                
            # Get volume
            total_volume = calls['volume'].sum() + puts['volume'].sum()
            
            return {
                'symbol': symbol,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'iv_30d': avg_iv,
                'iv_60d': avg_iv,  # Use 30d as proxy
                'iv_90d': avg_iv,  # Use 30d as proxy
                'atm_iv_call': call_iv,
                'atm_iv_put': put_iv,
                'iv_skew': iv_skew,
                'underlying_price': current_price,
                'volume': int(total_volume) if pd.notna(total_volume) else 0,
                'data_points': len(calls) + len(puts)
            }
            
        except Exception as e:
            logger.error(f"Error collecting Yahoo IV for {symbol}: {e}")
            return None
            
    def store_iv_data(self, data: Dict):
        """Store IV data in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO historical_iv
                (symbol, date, iv_30d, iv_60d, iv_90d, atm_iv_call, atm_iv_put,
                 iv_skew, underlying_price, volume, data_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['symbol'],
                data['date'],
                data['iv_30d'],
                data['iv_60d'],
                data['iv_90d'],
                data['atm_iv_call'],
                data['atm_iv_put'],
                data['iv_skew'],
                data['underlying_price'],
                data['volume'],
                data['data_points']
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing data: {e}")
            return False
        finally:
            conn.close()
            
    def log_collection_status(self, symbol: str, status: str, iv_30d: Optional[float] = None, 
                            error_message: Optional[str] = None):
        """Log collection status for monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO iv_collection_log
            (date, symbol, status, iv_30d, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime('%Y-%m-%d'),
            symbol,
            status,
            iv_30d,
            error_message
        ))
        
        conn.commit()
        conn.close()
        
    def run_daily_collection(self):
        """Run daily IV collection for all symbols."""
        logger.info(f"Starting daily IV collection for {len(self.symbols)} symbols")
        
        success_count = 0
        failed_count = 0
        
        for symbol in self.symbols:
            logger.info(f"Collecting {symbol}...")
            
            # Skip SPY if we already have data from Market Chameleon
            if symbol == 'SPY' and self.check_spy_data_exists():
                logger.info(f"Skipping {symbol} - already have Market Chameleon data")
                continue
                
            # Collect IV data
            iv_data = self.collect_yahoo_iv(symbol)
            
            if iv_data:
                # Store in database
                if self.store_iv_data(iv_data):
                    success_count += 1
                    self.log_collection_status(
                        symbol, 
                        'success', 
                        iv_data['iv_30d']
                    )
                    logger.info(f"✓ {symbol}: IV={iv_data['iv_30d']:.1%}")
                else:
                    failed_count += 1
                    self.log_collection_status(
                        symbol, 
                        'storage_error', 
                        iv_data['iv_30d'],
                        'Failed to store in database'
                    )
            else:
                failed_count += 1
                self.log_collection_status(
                    symbol, 
                    'fetch_error',
                    error_message='Failed to fetch IV data'
                )
                logger.error(f"✗ {symbol}: Failed to collect IV data")
                
        # Summary
        logger.info(f"\nCollection complete: {success_count} successful, {failed_count} failed")
        
        # Generate summary report
        self.generate_summary_report()
        
    def check_spy_data_exists(self) -> bool:
        """Check if we already have SPY data for today."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check both tables
        result = cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT 1 FROM spy_historical_iv WHERE date = ?
                UNION
                SELECT 1 FROM historical_iv WHERE symbol = 'SPY' AND date = ?
            )
        """, (today, today)).fetchone()[0]
        
        conn.close()
        return result > 0
        
    def generate_summary_report(self):
        """Generate summary of IV data collection."""
        conn = sqlite3.connect(self.db_path)
        
        # Get today's collection status
        today = datetime.now().strftime('%Y-%m-%d')
        
        status_query = """
            SELECT symbol, status, iv_30d, error_message
            FROM iv_collection_log
            WHERE date = ?
            ORDER BY symbol
        """
        
        status_df = pd.read_sql_query(status_query, conn, params=(today,))
        
        # Get overall data coverage
        coverage_query = """
            SELECT 
                symbol,
                COUNT(DISTINCT date) as days_collected,
                MIN(date) as first_date,
                MAX(date) as last_date,
                AVG(iv_30d) as avg_iv
            FROM historical_iv
            WHERE iv_30d > 0
            GROUP BY symbol
            ORDER BY symbol
        """
        
        coverage_df = pd.read_sql_query(coverage_query, conn)
        
        conn.close()
        
        # Log summary
        logger.info("\n=== Today's Collection Summary ===")
        for _, row in status_df.iterrows():
            status_icon = "✓" if row['status'] == 'success' else "✗"
            iv_str = f"{row['iv_30d']:.1%}" if pd.notna(row['iv_30d']) else "N/A"
            logger.info(f"{status_icon} {row['symbol']}: {row['status']} - IV: {iv_str}")
            
        logger.info("\n=== Overall Data Coverage ===")
        for _, row in coverage_df.iterrows():
            logger.info(f"{row['symbol']}: {row['days_collected']} days "
                       f"({row['first_date']} to {row['last_date']}), "
                       f"Avg IV: {row['avg_iv']:.1%}")
                       
    def calculate_iv_ranks(self):
        """Calculate IV ranks for all symbols with sufficient data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create IV ranks table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iv_ranks (
                symbol TEXT,
                date DATE,
                iv_rank_30d FLOAT,
                iv_rank_60d FLOAT,
                iv_rank_90d FLOAT,
                iv_rank_252d FLOAT,
                iv_percentile_30d FLOAT,
                iv_percentile_60d FLOAT,
                iv_percentile_90d FLOAT,
                iv_percentile_252d FLOAT,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # Get symbols with data
        symbols = pd.read_sql_query(
            "SELECT DISTINCT symbol FROM historical_iv WHERE iv_30d > 0",
            conn
        )['symbol'].tolist()
        
        for symbol in symbols:
            # Get historical data
            df = pd.read_sql_query(
                """
                SELECT date, iv_30d 
                FROM historical_iv 
                WHERE symbol = ? AND iv_30d > 0
                ORDER BY date
                """,
                conn,
                params=(symbol,)
            )
            
            if len(df) < 30:
                continue
                
            # Calculate rolling IV ranks
            for lookback in [30, 60, 90, 252]:
                if len(df) >= lookback:
                    # IV Rank
                    df[f'iv_rank_{lookback}d'] = df['iv_30d'].rolling(lookback).apply(
                        lambda x: ((x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100) 
                        if x.max() > x.min() else 50
                    )
                    
                    # IV Percentile
                    df[f'iv_percentile_{lookback}d'] = df['iv_30d'].rolling(lookback).apply(
                        lambda x: (x < x.iloc[-1]).sum() / len(x) * 100
                    )
                    
            # Store latest ranks
            latest = df.iloc[-1]
            cursor.execute("""
                INSERT OR REPLACE INTO iv_ranks
                (symbol, date, iv_rank_30d, iv_rank_60d, iv_rank_90d, iv_rank_252d,
                 iv_percentile_30d, iv_percentile_60d, iv_percentile_90d, iv_percentile_252d)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                latest['date'],
                latest.get('iv_rank_30d'),
                latest.get('iv_rank_60d'),
                latest.get('iv_rank_90d'),
                latest.get('iv_rank_252d'),
                latest.get('iv_percentile_30d'),
                latest.get('iv_percentile_60d'),
                latest.get('iv_percentile_90d'),
                latest.get('iv_percentile_252d')
            ))
            
        conn.commit()
        conn.close()


def main():
    """Main entry point for cron job."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Initialize collector
    collector = DailyIVCollector()
    
    # Run collection
    collector.run_daily_collection()
    
    # Calculate IV ranks
    collector.calculate_iv_ranks()
    
    logger.info("Daily IV collection complete!")


if __name__ == "__main__":
    main()