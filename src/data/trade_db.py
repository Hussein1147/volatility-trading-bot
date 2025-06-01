#!/usr/bin/env python3
"""
Lightweight SQLite database for storing trade history and Claude analyses
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import threading

class TradeDatabase:
    """SQLite database for trade and analysis history"""
    
    def __init__(self, db_path: str = "trade_history.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claude_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    percent_change REAL NOT NULL,
                    iv_rank REAL NOT NULL,
                    volume INTEGER,
                    should_trade BOOLEAN NOT NULL,
                    spread_type TEXT,
                    short_strike REAL,
                    long_strike REAL,
                    expiration_days INTEGER,
                    contracts INTEGER,
                    expected_credit REAL,
                    confidence INTEGER NOT NULL,
                    reasoning TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    raw_response TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    spread_type TEXT NOT NULL,
                    short_strike REAL NOT NULL,
                    long_strike REAL NOT NULL,
                    contracts INTEGER NOT NULL,
                    credit REAL NOT NULL,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    analysis_id INTEGER,
                    FOREIGN KEY (analysis_id) REFERENCES claude_analyses(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    scan_data TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message TEXT NOT NULL,
                    level TEXT DEFAULT 'INFO'
                )
            """)
            
            # Create indexes for better query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_timestamp ON claude_analyses(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_symbol ON claude_analyses(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON bot_logs(timestamp DESC)")
            
            conn.commit()
    
    def add_claude_analysis(self, analysis_data: Dict) -> int:
        """Add Claude analysis to database"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                market_data = analysis_data['market_data']
                claude_analysis = analysis_data.get('claude_analysis', {})
                
                cursor.execute("""
                    INSERT INTO claude_analyses (
                        timestamp, symbol, current_price, percent_change, iv_rank, volume,
                        should_trade, spread_type, short_strike, long_strike, expiration_days,
                        contracts, expected_credit, confidence, reasoning, decision, mode, raw_response
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_data['timestamp'],
                    analysis_data['symbol'],
                    market_data['current_price'],
                    market_data['percent_change'],
                    market_data['iv_rank'],
                    market_data.get('volume', 0),
                    claude_analysis.get('should_trade', False) if claude_analysis else False,
                    claude_analysis.get('spread_type') if claude_analysis else None,
                    claude_analysis.get('short_strike') if claude_analysis else None,
                    claude_analysis.get('long_strike') if claude_analysis else None,
                    claude_analysis.get('expiration_days') if claude_analysis else None,
                    claude_analysis.get('contracts') if claude_analysis else None,
                    claude_analysis.get('expected_credit') if claude_analysis else None,
                    claude_analysis.get('confidence', 0) if claude_analysis else 0,
                    claude_analysis.get('reasoning', 'Analysis failed') if claude_analysis else 'Analysis failed',
                    analysis_data['decision'],
                    analysis_data.get('mode', 'LIVE'),
                    json.dumps(claude_analysis) if claude_analysis else None
                ))
                
                return cursor.lastrowid
    
    def add_trade(self, trade_data: Dict, analysis_id: Optional[int] = None) -> int:
        """Add executed trade to database"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO trades (
                        symbol, spread_type, short_strike, long_strike,
                        contracts, credit, status, mode, analysis_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data['symbol'],
                    trade_data['spread_type'],
                    trade_data['short_strike'],
                    trade_data['long_strike'],
                    trade_data['contracts'],
                    trade_data['credit'],
                    trade_data.get('status', 'SIMULATED'),
                    trade_data.get('mode', 'DEV'),
                    analysis_id
                ))
                
                return cursor.lastrowid
    
    def add_log(self, message: str, level: str = 'INFO'):
        """Add bot log entry"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO bot_logs (message, level) VALUES (?, ?)",
                    (message, level)
                )
    
    def add_market_scan(self, scan_data: List[Dict]):
        """Add market scan data"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO market_scans (scan_data) VALUES (?)",
                    (json.dumps(scan_data),)
                )
    
    def get_claude_analyses(self, limit: int = 100, symbol: Optional[str] = None,
                           decision_filter: Optional[str] = None) -> List[Dict]:
        """Get Claude analyses with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM claude_analyses WHERE 1=1"
            params = []
            
            if symbol and symbol != "All":
                query += " AND symbol = ?"
                params.append(symbol)
            
            if decision_filter == "EXECUTE TRADE":
                query += " AND decision LIKE '%EXECUTE%'"
            elif decision_filter == "NO TRADE":
                query += " AND decision LIKE '%NO TRADE%'"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades(self, limit: int = 100, status: Optional[str] = None) -> List[Dict]:
        """Get trades with optional status filter"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_bot_logs(self, limit: int = 50) -> List[str]:
        """Get recent bot logs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT timestamp, message FROM bot_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [f"[{row[0]}] {row[1]}" for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total analyses
            cursor = conn.execute("SELECT COUNT(*) FROM claude_analyses")
            stats['total_analyses'] = cursor.fetchone()[0]
            
            # Trade decisions
            cursor = conn.execute("SELECT COUNT(*) FROM claude_analyses WHERE decision LIKE '%EXECUTE%'")
            stats['trade_signals'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM claude_analyses WHERE decision LIKE '%NO TRADE%'")
            stats['no_trade_signals'] = cursor.fetchone()[0]
            
            # Total trades
            cursor = conn.execute("SELECT COUNT(*) FROM trades")
            stats['total_trades'] = cursor.fetchone()[0]
            
            # Average confidence
            cursor = conn.execute("SELECT AVG(confidence) FROM claude_analyses WHERE confidence > 0")
            result = cursor.fetchone()[0]
            stats['avg_confidence'] = result if result else 0
            
            # Symbols analyzed
            cursor = conn.execute("SELECT COUNT(DISTINCT symbol) FROM claude_analyses")
            stats['unique_symbols'] = cursor.fetchone()[0]
            
            return stats
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to prevent database bloat"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                conn.execute("DELETE FROM claude_analyses WHERE timestamp < ?", (cutoff_date,))
                conn.execute("DELETE FROM trades WHERE timestamp < ?", (cutoff_date,))
                conn.execute("DELETE FROM bot_logs WHERE timestamp < ?", (cutoff_date,))
                conn.execute("DELETE FROM market_scans WHERE timestamp < ?", (cutoff_date,))
                
                # Vacuum to reclaim space
                conn.execute("VACUUM")

# Global database instance
trade_db = TradeDatabase()