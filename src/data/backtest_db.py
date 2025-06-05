"""
Database management for backtest results
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

class BacktestDatabase:
    def __init__(self, db_path: str = "backtest_results.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get a thread-local database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        
        # Create tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS backtest_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                start_date DATE,
                end_date DATE,
                initial_capital REAL,
                final_capital REAL,
                total_pnl REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                max_drawdown_pct REAL,
                profit_factor REAL,
                avg_win REAL,
                avg_loss REAL,
                avg_days_in_trade REAL,
                config TEXT,
                notes TEXT
            );
            
            CREATE TABLE IF NOT EXISTS backtest_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                symbol TEXT,
                spread_type TEXT,
                short_strike REAL,
                long_strike REAL,
                contracts INTEGER,
                entry_credit REAL,
                exit_cost REAL,
                realized_pnl REAL,
                max_profit REAL,
                max_loss REAL,
                exit_reason TEXT,
                days_in_trade INTEGER,
                confidence_score INTEGER,
                confidence_breakdown TEXT,
                FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id)
            );
            
            CREATE TABLE IF NOT EXISTS backtest_analyses (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                timestamp TIMESTAMP,
                symbol TEXT,
                current_price REAL,
                percent_change REAL,
                volume INTEGER,
                iv_rank REAL,
                should_trade BOOLEAN,
                spread_type TEXT,
                short_strike REAL,
                long_strike REAL,
                contracts INTEGER,
                expected_credit REAL,
                confidence INTEGER,
                reasoning TEXT,
                raw_response TEXT,
                FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_trades_run_id ON backtest_trades(run_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_run_id ON backtest_analyses(run_id);
            CREATE INDEX IF NOT EXISTS idx_trades_symbol ON backtest_trades(symbol);
            CREATE INDEX IF NOT EXISTS idx_trades_pnl ON backtest_trades(realized_pnl);
            CREATE INDEX IF NOT EXISTS idx_analyses_confidence ON backtest_analyses(confidence);
        """)
        conn.commit()
        conn.close()
    
    def save_backtest_run(self, config: Dict, results: Any, notes: str = "") -> int:
        """Save a complete backtest run and return run_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO backtest_runs (
                start_date, end_date, initial_capital, final_capital,
                total_pnl, total_trades, winning_trades, losing_trades,
                win_rate, sharpe_ratio, max_drawdown, max_drawdown_pct,
                profit_factor, avg_win, avg_loss, avg_days_in_trade,
                config, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config.start_date.date(),
            config.end_date.date(),
            config.initial_capital,
            config.initial_capital + results.total_pnl,
            results.total_pnl,
            results.total_trades,
            results.winning_trades,
            results.losing_trades,
            results.win_rate,
            results.sharpe_ratio,
            results.max_drawdown,
            results.max_drawdown_pct,
            results.profit_factor,
            results.avg_win,
            results.avg_loss,
            results.avg_days_in_trade,
            json.dumps({
                'symbols': config.symbols,
                'min_iv_rank': config.min_iv_rank,
                'min_price_move': config.min_price_move,
                'confidence_threshold': config.confidence_threshold,
                'max_risk_per_trade': config.max_risk_per_trade,
                'use_real_data': config.use_real_data
            }),
            notes
        ))
        
        run_id = cursor.lastrowid
        
        # Save all trades
        for trade in results.trades:
            self.save_trade(run_id, trade, conn)
        
        conn.commit()
        conn.close()
        return run_id
    
    def save_trade(self, run_id: int, trade: Any, conn=None):
        """Save individual trade"""
        if conn is None:
            conn = self.get_connection()
            close_conn = True
        else:
            close_conn = False
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO backtest_trades (
                run_id, entry_time, exit_time, symbol, spread_type,
                short_strike, long_strike, contracts, entry_credit,
                exit_cost, realized_pnl, max_profit, max_loss,
                exit_reason, days_in_trade, confidence_score,
                confidence_breakdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            trade.entry_time,
            trade.exit_time,
            trade.symbol,
            trade.spread_type,
            trade.short_strike,
            trade.long_strike,
            trade.contracts,
            trade.entry_credit,
            trade.exit_cost,
            trade.realized_pnl,
            trade.max_profit,
            trade.max_loss,
            trade.exit_reason,
            trade.days_in_trade,
            trade.confidence_score,
            json.dumps(trade.confidence_breakdown) if trade.confidence_breakdown else None
        ))
        
        if close_conn:
            conn.commit()
            conn.close()
    
    def save_analysis(self, run_id: int, timestamp: datetime, symbol: str, 
                     market_data: Dict, analysis: Optional[Dict], raw_response: str = ""):
        """Save Claude's analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO backtest_analyses (
                run_id, timestamp, symbol, current_price, percent_change,
                volume, iv_rank, should_trade, spread_type, short_strike,
                long_strike, contracts, expected_credit, confidence,
                reasoning, raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            timestamp,
            symbol,
            market_data.get('current_price'),
            market_data.get('percent_change'),
            market_data.get('volume'),
            market_data.get('iv_rank'),
            analysis.get('should_trade') if analysis else False,
            analysis.get('spread_type') if analysis else None,
            analysis.get('short_strike') if analysis else None,
            analysis.get('long_strike') if analysis else None,
            analysis.get('contracts') if analysis else None,
            analysis.get('expected_credit') if analysis else None,
            analysis.get('confidence') if analysis else None,
            analysis.get('reasoning') if analysis else None,
            raw_response
        ))
        conn.commit()
        conn.close()
    
    def get_backtest_runs(self, limit: int = 50) -> List[Dict]:
        """Get recent backtest runs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM backtest_runs 
            ORDER BY run_timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_run_trades(self, run_id: int) -> List[Dict]:
        """Get all trades for a specific run"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM backtest_trades 
            WHERE run_id = ? 
            ORDER BY entry_time
        """, (run_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_run_analyses(self, run_id: int) -> List[Dict]:
        """Get all analyses for a specific run"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM backtest_analyses 
            WHERE run_id = ? 
            ORDER BY timestamp
        """, (run_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_performance_comparison(self, run_ids: List[int]) -> pd.DataFrame:
        """Compare performance across multiple runs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(run_ids))
        cursor.execute(f"""
            SELECT 
                run_id,
                run_timestamp,
                total_pnl,
                win_rate,
                sharpe_ratio,
                max_drawdown_pct,
                profit_factor,
                total_trades,
                config
            FROM backtest_runs 
            WHERE run_id IN ({placeholders})
        """, run_ids)
        
        df = pd.DataFrame([dict(row) for row in cursor.fetchall()])
        if not df.empty:
            # Parse config for easier analysis
            df['config_parsed'] = df['config'].apply(json.loads)
            df['min_iv_rank'] = df['config_parsed'].apply(lambda x: x.get('min_iv_rank'))
            df['confidence_threshold'] = df['config_parsed'].apply(lambda x: x.get('confidence_threshold'))
        
        conn.close()
        return df
    
    def get_confidence_analysis(self, run_id: int) -> pd.DataFrame:
        """Analyze confidence scores vs outcomes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.confidence_score,
                t.realized_pnl,
                t.exit_reason,
                t.days_in_trade,
                a.reasoning
            FROM backtest_trades t
            LEFT JOIN backtest_analyses a ON 
                t.symbol = a.symbol AND 
                t.run_id = a.run_id AND
                DATE(t.entry_time) = DATE(a.timestamp)
            WHERE t.run_id = ?
        """, (run_id,))
        
        df = pd.DataFrame([dict(row) for row in cursor.fetchall()])
        conn.close()
        return df
    
    def close(self):
        """Close database connection"""
        # No longer needed since we create connections on demand
        pass

# Create global instance
backtest_db = BacktestDatabase()