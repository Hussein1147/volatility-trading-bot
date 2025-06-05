import os
import asyncio
import json
from datetime import datetime, timedelta, date
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple, Any
import logging
from decimal import Decimal
import threading

# Alpaca and other imports
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderType
from alpaca.data.live import StockDataStream
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
from alpaca.data.timeframe import TimeFrame

from anthropic import AsyncAnthropic
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# FastAPI for health checks
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Database integration
from src.data.database import DatabaseManager, Trade, MarketSnapshot, PerformanceMetric

# Position sizing
from src.core.position_sizer import DynamicPositionSizer

# Strike selection
from src.core.strike_selector import DeltaStrikeSelector

# Load environment variables
load_dotenv()

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    symbol: str
    current_price: float
    percent_change: float
    volume: int
    iv_rank: float
    iv_percentile: float
    high_iv_strikes: List[Tuple[float, float]]  # (strike, iv) pairs
    sma_20: Optional[float] = None
    rsi_14: Optional[float] = None
    news_catalyst: Optional[str] = None

@dataclass
class CreditSpreadSignal:
    symbol: str
    spread_type: str  # 'call_credit' or 'put_credit'
    short_strike: float
    long_strike: float
    expiration: str
    contracts: int
    credit_received: float
    max_loss: float
    probability_profit: float
    confidence: float
    reasoning: str

class HealthCheckAPI:
    def __init__(self, bot):
        self.app = FastAPI(title="Volatility Trading Bot API")
        self.bot = bot
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            try:
                # Check database connection
                async with self.bot.db.get_session() as session:
                    await session.execute("SELECT 1")
                
                # Check bot status
                status = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "active_trades": len(self.bot.active_trades),
                    "last_scan": self.bot.last_scan_time.isoformat() if self.bot.last_scan_time else None,
                    "database": "connected"
                }
                return JSONResponse(content=status)
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail="Service unhealthy")
        
        @self.app.get("/status")
        async def bot_status():
            try:
                performance = await self.bot.db.get_performance_summary()
                open_trades = await self.bot.db.get_open_trades()
                
                return JSONResponse(content={
                    "bot_status": "running" if self.bot.is_running else "stopped",
                    "performance": performance,
                    "open_trades_count": len(open_trades),
                    "account_balance": self.bot.account_balance,
                    "market_hours": self.bot.is_market_hours()
                })
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                raise HTTPException(status_code=500, detail="Status check failed")
    
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8080, log_level="info")

class EnhancedAlpacaVolatilityBot:
    def __init__(self):
        # Database setup
        database_url = os.getenv('DATABASE_URL', 'postgresql://bot_user:bot_password@localhost:5432/trading_bot')
        self.db = DatabaseManager(database_url)
        
        # Initialize Alpaca clients
        self.trading_client = TradingClient(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            paper=True  # Use paper trading
        )
        
        self.data_client = StockHistoricalDataClient(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY')
        )
        
        self.stream_client = StockDataStream(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY')
        )
        
        # Initialize Claude
        self.anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Trading parameters
        self.symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLE', 'XLK']
        self.account_balance = 10000
        self.max_risk_per_trade = 0.02  # 2% max risk (will be overridden by dynamic sizing)
        self.profit_target_percent = 0.50  # 50% of max profit (professional strategy)
        self.min_iv_rank = 40  # Minimum IV rank to consider (lowered from 70 for professional strategy)
        self.min_price_move = 1.5  # Minimum % move to trigger
        self.active_trades = []
        
        # Initialize dynamic position sizer
        self.position_sizer = DynamicPositionSizer(self.account_balance)
        
        # Initialize delta-based strike selector
        self.strike_selector = DeltaStrikeSelector(target_delta=0.15)
        
        # Options parameters
        self.dte_min = 7
        self.dte_max = 45
        self.delta_target_short = 0.15  # 15 delta for short strike (professional strategy)
        
        # Bot state
        self.is_running = False
        self.last_scan_time = None
        
        # Performance tracking
        self.daily_pnl = 0
        self.trade_count = 0
        
    def is_market_hours(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Weekend
            return False
            
        return market_open <= now <= market_close
    
    async def get_account_info(self):
        """Get current account information"""
        try:
            account = self.trading_client.get_account()
            self.account_balance = float(account.cash)
            
            await self.db.log_bot_event(
                "INFO", 
                f"Account Balance: ${account.cash}, Buying Power: ${account.buying_power}",
                "volatility_bot",
                "get_account_info"
            )
            
            logger.info(f"Account Balance: ${account.cash}")
            logger.info(f"Buying Power: ${account.buying_power}")
            return account
        except Exception as e:
            await self.db.log_bot_event("ERROR", f"Error getting account info: {e}")
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def calculate_iv_metrics(self, symbol: str) -> Tuple[float, float]:
        """Calculate IV rank and percentile for a symbol"""
        try:
            # Get historical data for IV calculation
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            bars = self.data_client.get_stock_bars(request)
            df = bars.df
            
            # Calculate historical volatility
            df['returns'] = df['close'].pct_change()
            df['hv_20'] = df['returns'].rolling(20).std() * np.sqrt(252) * 100
            
            # For demo purposes, using HV as proxy for IV
            # In production, you'd use actual options data
            current_hv = df['hv_20'].iloc[-1]
            hv_min = df['hv_20'].min()
            hv_max = df['hv_20'].max()
            
            # Calculate IV rank and percentile
            iv_rank = ((current_hv - hv_min) / (hv_max - hv_min)) * 100
            iv_percentile = (df['hv_20'] < current_hv).sum() / len(df['hv_20']) * 100
            
            return iv_rank, iv_percentile
            
        except Exception as e:
            logger.error(f"Error calculating IV metrics: {e}")
            await self.db.log_bot_event("ERROR", f"Error calculating IV metrics for {symbol}: {e}")
            return 50.0, 50.0  # Default values
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Fetch current market data and check for significant moves"""
        try:
            # Get latest quote
            request = StockQuotesRequest(
                symbol_or_symbols=symbol,
                limit=1
            )
            quotes = self.data_client.get_stock_latest_quote(request)
            current_price = float(quotes[symbol].ask_price)
            
            # Get today's bars for % change and technical indicators
            # Get 30 days of history for SMA and RSI calculation
            history_request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now().date() - timedelta(days=30),
                end=datetime.now().date()
            )
            bars = self.data_client.get_stock_bars(history_request)
            
            if not bars.df.empty:
                df = bars.df
                # Get today's data
                today_data = df.iloc[-1] if len(df) > 0 else None
                if today_data is not None:
                    open_price = float(today_data['open'])
                    percent_change = ((current_price - open_price) / open_price) * 100
                    volume = int(today_data['volume'])
                    
                    # Calculate technical indicators
                    # SMA 20
                    if len(df) >= 20:
                        sma_20 = float(df['close'].tail(20).mean())
                    else:
                        sma_20 = float(df['close'].mean())
                    
                    # RSI 14
                    if len(df) >= 14:
                        delta = df['close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi_14 = float(100 - (100 / (1 + rs.iloc[-1])))
                    else:
                        rsi_14 = 50.0  # Default neutral RSI
                else:
                    percent_change = 0
                    volume = 0
                    sma_20 = current_price
                    rsi_14 = 50.0
            else:
                percent_change = 0
                volume = 0
                sma_20 = current_price
                rsi_14 = 50.0
            
            # Calculate IV metrics
            iv_rank, iv_percentile = await self.calculate_iv_metrics(symbol)
            
            # Save market snapshot to database
            snapshot_data = {
                'symbol': symbol,
                'current_price': current_price,
                'percent_change': percent_change,
                'volume': volume,
                'iv_rank': iv_rank,
                'iv_percentile': iv_percentile,
                'news_catalyst': "Market volatility event detected" if abs(percent_change) >= self.min_price_move else None
            }
            await self.db.save_market_snapshot(snapshot_data)
            
            # Check if this is a significant move
            if abs(percent_change) >= self.min_price_move and iv_rank >= self.min_iv_rank:
                return MarketData(
                    symbol=symbol,
                    current_price=current_price,
                    percent_change=percent_change,
                    volume=volume,
                    iv_rank=iv_rank,
                    iv_percentile=iv_percentile,
                    high_iv_strikes=[],  # Would populate with actual options data
                    sma_20=sma_20,
                    rsi_14=rsi_14,
                    news_catalyst="Market volatility event detected"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            await self.db.log_bot_event("ERROR", f"Error getting market data for {symbol}: {e}")
            return None
    
    async def analyze_with_claude(self, market_data: MarketData) -> Optional[CreditSpreadSignal]:
        """Use Claude to analyze market conditions and suggest credit spread"""
        
        prompt = f"""
        Analyze this volatility spike for a credit spread opportunity:
        
        Symbol: {market_data.symbol}
        Current Price: ${market_data.current_price:.2f}
        Today's Move: {market_data.percent_change:.2f}%
        Volume: {market_data.volume:,}
        IV Rank: {market_data.iv_rank:.1f}
        IV Percentile: {market_data.iv_percentile:.1f}
        
        Technical Indicators:
        20-day SMA: ${market_data.sma_20:.2f}
        14-day RSI: {market_data.rsi_14:.1f}
        Price vs SMA: {"Above" if market_data.current_price > market_data.sma_20 else "Below"} SMA
        
        Account Balance: ${self.account_balance}
        Max Risk per Trade: {self.max_risk_per_trade * 100}%
        
        IMPORTANT Directional Filter Rules:
        - PUT CREDIT SPREADS: ONLY if price > SMA AND RSI > 50
        - CALL CREDIT SPREADS: ONLY if price < SMA AND RSI < 50
        - If conditions don't match, DO NOT TRADE
        
        Strategy Rules:
        1. Check directional filters FIRST - if they don't match, set should_trade = false
        2. If filters pass and big move DOWN: Sell CALL credit spread above resistance
        3. If filters pass and big move UP: Sell PUT credit spread below support
        4. Target 15 delta for short strike (approximately 85% probability of profit)
        5. Use 40-50 DTE for primary book, 7-14 DTE only if IV Rank >= 80
        6. Calculate confidence score based on multiple factors
        
        Confidence Scoring (start at 50, add/subtract):
        - IV Rank 40-60: +5, 60-80: +10, 80+: +15
        - Price move 1.5-2%: +5, 2-3%: +10, 3%+: +15
        - Volume above average: +5
        - Directional alignment strong: +10
        - Strike distance good (1.5-2 SD): +10
        - DTE in sweet spot (40-50): +5
        - Subtract for risks: earnings nearby -10, major support/resistance breach -5
        
        Provide analysis in JSON format:
        {{
            "should_trade": true/false,
            "spread_type": "call_credit" or "put_credit", 
            "expiration_days": number,
            "volatility_estimate": decimal (e.g., 0.25 for 25% IV),
            "confidence": 0-100,
            "confidence_factors": {{
                "iv_rank_score": number,
                "price_move_score": number,
                "volume_score": number,
                "directional_score": number,
                "dte_score": number,
                "risk_deductions": number,
                "total": number
            }},
            "reasoning": "explanation"
        }}
        """
        
        try:
            response = await self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis = json.loads(response.content[0].text)
            
            if analysis['should_trade']:
                # Use delta-based strike selection
                expiration_days = analysis['expiration_days']
                volatility = analysis.get('volatility_estimate', 0.25)  # Default 25% if not provided
                
                # Get strikes based on delta
                short_strike, long_strike = self.strike_selector.select_spread_strikes(
                    symbol=market_data.symbol,
                    spot_price=market_data.current_price,
                    spread_type=analysis['spread_type'],
                    dte=expiration_days,
                    volatility=volatility,
                    spread_width=5.0  # Default $5 wide spreads
                )
                
                # Calculate spread details
                spread_width = abs(long_strike - short_strike)
                
                # Estimate credit (simplified - in reality would need option chain)
                # Credit roughly = spread_width * 0.20 for 15 delta spreads
                expected_credit_per_contract = spread_width * 0.20
                max_loss_per_contract = (spread_width * 100) - expected_credit_per_contract
                
                # Calculate Greeks for the spread
                spread_greeks = self.strike_selector.calculate_spread_greeks(
                    spot_price=market_data.current_price,
                    short_strike=short_strike,
                    long_strike=long_strike,
                    dte=expiration_days,
                    volatility=volatility,
                    spread_type=analysis['spread_type'],
                    contracts=1
                )
                
                # Determine book type based on DTE
                if expiration_days >= 40:
                    book_type = 'PRIMARY'
                elif 7 <= expiration_days <= 14 and market_data.iv_rank >= 80:
                    book_type = 'INCOME_POP'
                else:
                    book_type = 'PRIMARY'  # Default
                
                # Use dynamic position sizing based on confidence
                position_size = self.position_sizer.calculate_position_size(
                    confidence=analysis['confidence'],
                    max_loss_per_contract=max_loss_per_contract,
                    book_type=book_type,
                    current_positions=self.active_trades
                )
                
                # Check if we got any contracts
                if position_size.contracts == 0:
                    logger.warning(f"Position sizing returned 0 contracts for {market_data.symbol}")
                    return None
                
                # Calculate actual values with sized position
                total_credit = expected_credit_per_contract * position_size.contracts * 100
                total_max_loss = position_size.total_max_loss
                
                # Store confidence factors if provided
                confidence_breakdown = analysis.get('confidence_factors', {})
                
                # Calculate probability of profit from delta (rough approximation)
                probability_profit = (1 - abs(spread_greeks['short_delta'])) * 100
                
                return CreditSpreadSignal(
                    symbol=market_data.symbol,
                    spread_type=analysis['spread_type'],
                    short_strike=short_strike,
                    long_strike=long_strike,
                    expiration=(datetime.now() + timedelta(days=expiration_days)).strftime('%Y-%m-%d'),
                    contracts=position_size.contracts,
                    credit_received=total_credit,
                    max_loss=total_max_loss,
                    probability_profit=probability_profit,
                    confidence=analysis['confidence'],
                    reasoning=f"{analysis['reasoning']} | Delta: {spread_greeks['short_delta']:.2f} | Risk: {position_size.confidence_tier} ({position_size.risk_percentage:.1%})"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing with Claude: {e}")
            await self.db.log_bot_event("ERROR", f"Error analyzing with Claude: {e}")
            return None
    
    async def execute_credit_spread(self, signal: CreditSpreadSignal) -> str:
        """Execute credit spread trade and save to database"""
        try:
            # Log the trade signal
            logger.info(f"\n{'='*50}")
            logger.info(f"EXECUTING CREDIT SPREAD:")
            logger.info(f"Symbol: {signal.symbol}")
            logger.info(f"Type: {signal.spread_type}")
            logger.info(f"Short Strike: ${signal.short_strike}")
            logger.info(f"Long Strike: ${signal.long_strike}")
            logger.info(f"Expiration: {signal.expiration}")
            logger.info(f"Contracts: {signal.contracts}")
            logger.info(f"Credit: ${signal.credit_received:.2f}")
            logger.info(f"Max Loss: ${signal.max_loss:.2f}")
            logger.info(f"Probability of Profit: {signal.probability_profit:.1f}%")
            logger.info(f"Confidence: {signal.confidence}%")
            logger.info(f"Reasoning: {signal.reasoning}")
            logger.info(f"{'='*50}\n")
            
            # Save trade to database
            trade_data = {
                'symbol': signal.symbol,
                'strategy_type': 'credit_spread',
                'spread_type': signal.spread_type,
                'short_strike': signal.short_strike,
                'long_strike': signal.long_strike,
                'expiration_date': datetime.strptime(signal.expiration, '%Y-%m-%d').date(),
                'contracts': signal.contracts,
                'credit_received': signal.credit_received,
                'max_loss': signal.max_loss,
                'probability_profit': signal.probability_profit,
                'confidence_score': signal.confidence,
                'claude_reasoning': signal.reasoning,
                'status': 'open'
            }
            
            trade_id = await self.db.save_trade(trade_data)
            
            # Create alert
            await self.db.create_alert(
                'trade_executed',
                f"Executed {signal.spread_type} on {signal.symbol} for ${signal.credit_received:.2f} credit",
                trade_id
            )
            
            # Track the paper trade
            self.active_trades.append({
                'trade_id': trade_id,
                'signal': signal,
                'entry_time': datetime.now(),
                'status': 'open',
                'target_profit': signal.credit_received * self.profit_target_percent
            })
            
            self.trade_count += 1
            
            await self.db.log_bot_event(
                "INFO", 
                f"Executed trade {trade_id}: {signal.spread_type} on {signal.symbol}",
                "volatility_bot",
                "execute_credit_spread",
                trade_id
            )
            
            return trade_id
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            await self.db.log_bot_event("ERROR", f"Error executing trade: {e}")
            raise
    
    async def monitor_positions(self):
        """Monitor open positions for profit targets or stop losses"""
        try:
            positions = self.trading_client.get_all_positions()
            
            for position in positions:
                # Check if position has reached profit target
                unrealized_pl = float(position.unrealized_pl)
                
                for trade in self.active_trades:
                    if trade['status'] == 'open' and trade['signal'].symbol == position.symbol:
                        if unrealized_pl >= trade['target_profit']:
                            logger.info(f"Profit target reached for {position.symbol}")
                            logger.info(f"Unrealized P/L: ${unrealized_pl:.2f}")
                            
                            # Update trade in database
                            await self.db.update_trade(
                                trade['trade_id'],
                                {
                                    'status': 'closed',
                                    'exit_time': datetime.utcnow(),
                                    'realized_pnl': unrealized_pl,
                                    'exit_price': float(position.current_price)
                                }
                            )
                            
                            # Create alert
                            await self.db.create_alert(
                                'profit_target',
                                f"Profit target reached for {position.symbol}: ${unrealized_pl:.2f}",
                                trade['trade_id']
                            )
                            
                            trade['status'] = 'closed'
                            self.daily_pnl += unrealized_pl
                            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            await self.db.log_bot_event("ERROR", f"Error monitoring positions: {e}")
    
    async def update_daily_performance(self):
        """Update daily performance metrics"""
        try:
            today = date.today()
            
            # Calculate metrics
            open_trades = await self.db.get_open_trades()
            performance_summary = await self.db.get_performance_summary(1)  # Today only
            
            total_trades = performance_summary.get('total_trades', 0)
            winning_trades = performance_summary.get('winning_trades', 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'daily_pnl': self.daily_pnl,
                'account_balance': self.account_balance,
                'win_rate': win_rate
            }
            
            await self.db.update_performance_metrics(today, metrics)
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
            await self.db.log_bot_event("ERROR", f"Error updating performance metrics: {e}")
    
    async def phase2_volatility_contraction(self, original_signal: CreditSpreadSignal):
        """Check for volatility contraction opportunity (Phase 2)"""
        await asyncio.sleep(3600)  # Wait 1 hour
        
        # Re-check market conditions
        market_data = await self.get_market_data(original_signal.symbol)
        
        if market_data and market_data.iv_rank < 60:  # IV has contracted
            logger.info("Volatility contraction detected - analyzing Phase 2 opportunity")
            await self.db.log_bot_event(
                "INFO",
                f"Volatility contraction detected for {original_signal.symbol} - Phase 2 opportunity"
            )
            # Could add butterfly or opposite side credit spread here
    
    async def scan_for_opportunities(self):
        """Main scanning loop for all symbols"""
        logger.info(f"Scanning {len(self.symbols)} symbols for opportunities...")
        self.last_scan_time = datetime.utcnow()
        
        for symbol in self.symbols:
            market_data = await self.get_market_data(symbol)
            
            if market_data:
                logger.info(f"Significant move detected in {symbol}: {market_data.percent_change:.2f}%")
                
                # Analyze with Claude
                signal = await self.analyze_with_claude(market_data)
                
                if signal and signal.confidence >= 70:
                    trade_id = await self.execute_credit_spread(signal)
                    
                    # Schedule phase 2 check
                    asyncio.create_task(self.phase2_volatility_contraction(signal))
    
    async def run_bot(self):
        """Main bot loop"""
        logger.info("="*60)
        logger.info("Enhanced Alpaca Volatility Trading Bot Started")
        logger.info("="*60)
        
        self.is_running = True
        
        # Get initial account info
        await self.get_account_info()
        
        logger.info(f"Monitoring symbols: {', '.join(self.symbols)}")
        logger.info(f"Min IV Rank: {self.min_iv_rank}")
        logger.info(f"Min Price Move: {self.min_price_move}%")
        logger.info(f"Max Risk per Trade: ${self.max_risk_per_trade * self.account_balance:.2f}")
        
        await self.db.log_bot_event("INFO", "Bot started successfully")
        
        while self.is_running:
            try:
                # Market hours check
                if self.is_market_hours():
                    await self.scan_for_opportunities()
                    await self.monitor_positions()
                    await self.update_daily_performance()
                else:
                    logger.info("Market closed - waiting...")
                
                # Wait before next scan
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Bot error: {e}")
                await self.db.log_bot_event("ERROR", f"Bot error: {e}")
                await asyncio.sleep(60)
    
    async def stop_bot(self):
        """Stop the bot gracefully"""
        logger.info("Stopping bot...")
        self.is_running = False
        await self.db.log_bot_event("INFO", "Bot stopped")
        await self.db.close()

async def main():
    """Main function to run bot and health check API"""
    bot = EnhancedAlpacaVolatilityBot()
    health_api = HealthCheckAPI(bot)
    
    # Start health check API in separate thread
    api_thread = threading.Thread(target=health_api.run, daemon=True)
    api_thread.start()
    
    try:
        # Run the trading bot
        await bot.run_bot()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.stop_bot()

if __name__ == "__main__":
    asyncio.run(main())