import os
import asyncio
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid

from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, Numeric, Boolean, Date, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    spread_type = Column(String(20))
    short_strike = Column(Numeric(10,2))
    long_strike = Column(Numeric(10,2))
    expiration_date = Column(Date)
    contracts = Column(Integer, nullable=False)
    entry_price = Column(Numeric(10,4))
    exit_price = Column(Numeric(10,4))
    credit_received = Column(Numeric(10,2))
    max_loss = Column(Numeric(10,2))
    realized_pnl = Column(Numeric(10,2))
    unrealized_pnl = Column(Numeric(10,2))
    probability_profit = Column(Numeric(5,2))
    confidence_score = Column(Integer)
    claude_reasoning = Column(Text)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)
    status = Column(String(20), default='open')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class MarketSnapshot(Base):
    __tablename__ = 'market_snapshots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False)
    current_price = Column(Numeric(10,2), nullable=False)
    percent_change = Column(Numeric(8,4))
    volume = Column(BigInteger)
    iv_rank = Column(Numeric(5,2))
    iv_percentile = Column(Numeric(5,2))
    news_catalyst = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class PerformanceMetric(Base):
    __tablename__ = 'performance_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, unique=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    daily_pnl = Column(Numeric(12,2), default=0)
    cumulative_pnl = Column(Numeric(12,2), default=0)
    account_balance = Column(Numeric(12,2))
    win_rate = Column(Numeric(5,2))
    profit_factor = Column(Numeric(8,4))
    max_drawdown = Column(Numeric(12,2))
    sharpe_ratio = Column(Numeric(8,4))
    created_at = Column(DateTime, default=datetime.utcnow)

class BotLog(Base):
    __tablename__ = 'bot_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(100))
    function_name = Column(String(100))
    trade_id = Column(UUID(as_uuid=True))
    timestamp = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    trade_id = Column(UUID(as_uuid=True))
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        return self.SessionLocal()
    
    async def save_trade(self, trade_data: Dict[str, Any]) -> str:
        """Save a new trade to the database"""
        async with self.SessionLocal() as session:
            try:
                trade = Trade(**trade_data)
                session.add(trade)
                await session.commit()
                await session.refresh(trade)
                logger.info(f"Saved trade {trade.id} to database")
                return str(trade.id)
            except Exception as e:
                await session.rollback()
                logger.error(f"Error saving trade: {e}")
                raise
    
    async def update_trade(self, trade_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing trade"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    text("UPDATE trades SET {} WHERE id = :trade_id").format(
                        ", ".join([f"{k} = :{k}" for k in update_data.keys()])
                    ),
                    {"trade_id": trade_id, **update_data}
                )
                await session.commit()
                return result.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating trade {trade_id}: {e}")
                raise
    
    async def save_market_snapshot(self, snapshot_data: Dict[str, Any]) -> str:
        """Save market data snapshot"""
        async with self.SessionLocal() as session:
            try:
                snapshot = MarketSnapshot(**snapshot_data)
                session.add(snapshot)
                await session.commit()
                await session.refresh(snapshot)
                return str(snapshot.id)
            except Exception as e:
                await session.rollback()
                logger.error(f"Error saving market snapshot: {e}")
                raise
    
    async def update_performance_metrics(self, date: date, metrics: Dict[str, Any]) -> bool:
        """Update daily performance metrics"""
        async with self.SessionLocal() as session:
            try:
                # Upsert performance metrics
                result = await session.execute(
                    text("""
                    INSERT INTO performance_metrics (date, {columns}) 
                    VALUES (:date, {values})
                    ON CONFLICT (date) 
                    DO UPDATE SET {updates}
                    """).format(
                        columns=", ".join(metrics.keys()),
                        values=", ".join([f":{k}" for k in metrics.keys()]),
                        updates=", ".join([f"{k} = EXCLUDED.{k}" for k in metrics.keys()])
                    ),
                    {"date": date, **metrics}
                )
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating performance metrics: {e}")
                raise
    
    async def log_bot_event(self, level: str, message: str, module: str = None, 
                           function_name: str = None, trade_id: str = None):
        """Log bot events to database"""
        async with self.SessionLocal() as session:
            try:
                log = BotLog(
                    log_level=level,
                    message=message,
                    module=module,
                    function_name=function_name,
                    trade_id=trade_id if trade_id else None
                )
                session.add(log)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error logging bot event: {e}")
    
    async def create_alert(self, alert_type: str, message: str, trade_id: str = None) -> str:
        """Create a new alert"""
        async with self.SessionLocal() as session:
            try:
                alert = Alert(
                    alert_type=alert_type,
                    message=message,
                    trade_id=trade_id if trade_id else None
                )
                session.add(alert)
                await session.commit()
                await session.refresh(alert)
                return str(alert.id)
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating alert: {e}")
                raise
    
    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    text("SELECT * FROM trades WHERE status = 'open' ORDER BY entry_time DESC")
                )
                return [dict(row._mapping) for row in result]
            except Exception as e:
                logger.error(f"Error fetching open trades: {e}")
                return []
    
    async def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get performance summary for the last N days"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    text("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(realized_pnl) as total_pnl,
                        AVG(realized_pnl) as avg_pnl,
                        MAX(realized_pnl) as best_trade,
                        MIN(realized_pnl) as worst_trade
                    FROM trades 
                    WHERE entry_time >= CURRENT_DATE - INTERVAL '{} days'
                    AND status = 'closed'
                    """.format(days))
                )
                row = result.first()
                return dict(row._mapping) if row else {}
            except Exception as e:
                logger.error(f"Error fetching performance summary: {e}")
                return {}
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()