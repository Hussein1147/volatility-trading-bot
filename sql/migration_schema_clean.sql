-- Phase 2 Migration: Multi-book support and enhanced tracking
-- This script only adds missing elements

-- Create portfolio metrics table
CREATE TABLE IF NOT EXISTS portfolio_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_delta REAL,
    total_theta REAL,
    total_vega REAL,
    total_gamma REAL,
    day_at_risk REAL,
    vix_level REAL,
    hedge_active BOOLEAN DEFAULT FALSE,
    portfolio_value REAL,
    open_positions INTEGER,
    primary_book_positions INTEGER,
    income_pop_positions INTEGER
);

-- Create strategy rules audit table
CREATE TABLE IF NOT EXISTS strategy_rules_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    rule_name TEXT,
    rule_version TEXT,
    backtest_results JSON,
    live_performance JSON,
    status TEXT -- 'testing', 'approved', 'deprecated'
);

-- Create confidence tracking table
CREATE TABLE IF NOT EXISTS confidence_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence_score INTEGER,
    iv_rank_score INTEGER,
    price_move_score INTEGER,
    volume_score INTEGER,
    directional_score INTEGER,
    strike_distance_score INTEGER,
    dte_score INTEGER,
    risk_deductions INTEGER,
    factors_json JSON,
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_trades_book_type ON trades(book_type);
CREATE INDEX IF NOT EXISTS idx_portfolio_metrics_timestamp ON portfolio_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_confidence_tracking_trade_id ON confidence_tracking(trade_id);

-- Update existing trades to have book_type
UPDATE trades SET book_type = 'PRIMARY' WHERE book_type IS NULL OR book_type = '';