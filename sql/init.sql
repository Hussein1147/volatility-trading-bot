-- Trading Bot Database Schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Trades table for storing all trade information
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL, -- 'credit_spread', 'butterfly', etc.
    spread_type VARCHAR(20), -- 'call_credit', 'put_credit', 'iron_condor'
    short_strike DECIMAL(10,2),
    long_strike DECIMAL(10,2),
    expiration_date DATE,
    contracts INTEGER NOT NULL,
    entry_price DECIMAL(10,4),
    exit_price DECIMAL(10,4),
    credit_received DECIMAL(10,2),
    max_loss DECIMAL(10,2),
    realized_pnl DECIMAL(10,2),
    unrealized_pnl DECIMAL(10,2),
    probability_profit DECIMAL(5,2),
    confidence_score INTEGER,
    claude_reasoning TEXT,
    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exit_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'closed', 'expired'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market data snapshots
CREATE TABLE market_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    current_price DECIMAL(10,2) NOT NULL,
    percent_change DECIMAL(8,4),
    volume BIGINT,
    iv_rank DECIMAL(5,2),
    iv_percentile DECIMAL(5,2),
    news_catalyst TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics tracking
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    daily_pnl DECIMAL(12,2) DEFAULT 0,
    cumulative_pnl DECIMAL(12,2) DEFAULT 0,
    account_balance DECIMAL(12,2),
    win_rate DECIMAL(5,2),
    profit_factor DECIMAL(8,4),
    max_drawdown DECIMAL(12,2),
    sharpe_ratio DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);

-- Bot execution logs
CREATE TABLE bot_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_level VARCHAR(10) NOT NULL, -- 'INFO', 'WARNING', 'ERROR'
    message TEXT NOT NULL,
    module VARCHAR(100),
    function_name VARCHAR(100),
    trade_id UUID REFERENCES trades(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts and notifications
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL, -- 'trade_executed', 'profit_target', 'stop_loss'
    message TEXT NOT NULL,
    trade_id UUID REFERENCES trades(id),
    is_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_entry_time ON trades(entry_time);
CREATE INDEX idx_market_snapshots_symbol ON market_snapshots(symbol);
CREATE INDEX idx_market_snapshots_timestamp ON market_snapshots(timestamp);
CREATE INDEX idx_performance_metrics_date ON performance_metrics(date);
CREATE INDEX idx_bot_logs_timestamp ON bot_logs(timestamp);
CREATE INDEX idx_bot_logs_level ON bot_logs(log_level);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_trades_updated_at 
    BEFORE UPDATE ON trades 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert initial performance record
INSERT INTO performance_metrics (date, account_balance) 
VALUES (CURRENT_DATE, 10000.00);