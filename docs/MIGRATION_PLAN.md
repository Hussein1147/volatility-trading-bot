# Migration Plan: Professional Multi-Book Strategy

## Executive Summary
This document outlines the migration from our current basic volatility trading strategy to the professional multi-book options income strategy. The migration will be executed over 8 weeks with careful testing and validation at each phase.

## Current State vs Target State

### Current Strategy
- **IV Threshold**: 70
- **Entry**: Min 1.5% price move + high IV
- **Strikes**: Fixed distance from current price
- **Position Size**: Fixed 1-2 contracts
- **Exit**: 35% profit target
- **Universe**: SPY, QQQ, IWM

### Target Strategy
- **IV Threshold**: 40 (3-5x more opportunities)
- **Entry**: Delta-based (Δ0.15) with directional filters
- **Position Size**: Dynamic 3-8% based on confidence
- **Exit**: 50% profit or 21 DTE
- **Universe**: SPY, QQQ, IWM, DIA, XLE, XLK
- **Multiple Books**: Primary (45 DTE) + Income-Pop (7-14 DTE)
- **Hedging**: VIX calls when needed

## Phase 1: Foundation & Data (Weeks 1-2)

### Week 1: Data Infrastructure
```python
# Required new data points
1. Technical Indicators:
   - 20-day SMA
   - 14-period RSI
   - Option Greeks (especially Delta)
   
2. Market Data:
   - Bid-ask spreads
   - VIX levels and options
   - Economic calendar (FOMC, CPI, NFP)
   
3. Extended Universe:
   - Add XLE (Energy Select SPDR)
   - Add XLK (Technology Select SPDR)
   - Add DIA (Dow Jones ETF)
```

**Implementation Tasks**:
- [ ] Enhance `AlpacaDataFetcher` with technical indicators
- [ ] Create `TechnicalAnalysis` module
- [ ] Add Greeks calculation/fetching
- [ ] Set up economic calendar API
- [ ] Validate data quality for new symbols

### Week 2: Database & Infrastructure
```sql
-- New database schema additions
ALTER TABLE trades ADD COLUMN book_type VARCHAR(20) DEFAULT 'PRIMARY';
ALTER TABLE trades ADD COLUMN entry_iv_rank REAL;
ALTER TABLE trades ADD COLUMN entry_delta REAL;
ALTER TABLE trades ADD COLUMN directional_filter_passed BOOLEAN;

CREATE TABLE portfolio_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_delta REAL,
    total_theta REAL,
    total_vega REAL,
    total_gamma REAL,
    day_at_risk REAL,
    vix_level REAL,
    hedge_active BOOLEAN DEFAULT FALSE
);

CREATE TABLE strategy_rules_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    rule_name TEXT,
    rule_version TEXT,
    backtest_results JSON,
    live_performance JSON,
    status TEXT -- 'testing', 'approved', 'deprecated'
);
```

## Phase 2: Core Logic Implementation (Weeks 3-4)

### Week 3: Strategy Selection & Entry Logic

#### 2.1 Enhanced Trade Analyzer
```python
class ProfessionalTradeAnalyzer:
    def __init__(self):
        self.min_iv_rank = 40  # Lowered from 70
        self.delta_target = 0.15
        self.credit_target_pct = 0.20  # 20% of width
        
    def analyze_opportunity(self, symbol_data):
        # Check IV rank threshold
        if symbol_data.iv_rank < self.min_iv_rank:
            return None
            
        # Apply directional filters
        if not self.passes_directional_filter(symbol_data):
            return None
            
        # Select strategy based on IV rank
        if symbol_data.iv_rank >= 65:
            return self.build_iron_condor(symbol_data)
        else:
            return self.build_vertical_spread(symbol_data)
    
    def passes_directional_filter(self, data):
        # Put spread filter
        if data.rsi > 50 and data.price > data.sma_20:
            data.allowed_direction = 'PUT'
            return True
        # Call spread filter  
        elif data.rsi < 50 and data.price < data.sma_20:
            data.allowed_direction = 'CALL'
            return True
        return False
```

#### 2.2 Multi-Book Management
```python
class MultiBookManager:
    def __init__(self):
        self.books = {
            'PRIMARY': {'target_dte': 45, 'dte_range': (40, 50)},
            'INCOME_POP': {'target_dte': 10, 'dte_range': (7, 14), 'min_iv': 80}
        }
        
    def route_trade(self, trade_setup, iv_rank):
        # Primary book routing
        if 40 <= trade_setup.dte <= 50:
            return 'PRIMARY'
        # Income-pop routing
        elif 7 <= trade_setup.dte <= 14 and iv_rank >= 80:
            return 'INCOME_POP'
        return None
```

### Week 4: Position Sizing & Risk Management

#### 2.3 Dynamic Position Sizing
```python
class DynamicPositionSizer:
    def __init__(self, account_balance):
        self.account_balance = account_balance
        self.risk_tiers = {
            (70, 79): 0.03,
            (80, 89): 0.05,
            (90, 100): 0.08
        }
        self.max_day_risk = 0.10
        self.income_pop_max_risk = 0.01
        
    def calculate_position_size(self, confidence, max_loss_per_contract, book_type='PRIMARY'):
        # Get risk percentage based on confidence
        risk_pct = self.get_risk_percentage(confidence, book_type)
        
        # Check day-at-risk limit
        current_day_risk = self.get_current_day_risk()
        if current_day_risk + risk_pct > self.max_day_risk:
            return 0
            
        # Calculate contracts
        risk_amount = self.account_balance * risk_pct
        contracts = int(risk_amount / max_loss_per_contract)
        
        return contracts
```

#### 2.4 Portfolio Greeks Manager
```python
class PortfolioGreeksManager:
    def __init__(self):
        self.delta_limit = 0.30
        self.vega_hedge_threshold = -1000  # Negative vega threshold
        
    def check_portfolio_limits(self, positions):
        total_delta = sum(p.delta * p.contracts * 100 for p in positions)
        
        if abs(total_delta) > self.delta_limit:
            return False, f"Portfolio delta {total_delta:.2f} exceeds limit"
            
        return True, "Portfolio within limits"
        
    def needs_vix_hedge(self, portfolio_vega, avg_iv_rank):
        return portfolio_vega < self.vega_hedge_threshold and avg_iv_rank > 60
```

## Phase 3: Advanced Features (Weeks 5-6)

### Week 5: Exit Management & Adjustments

#### 3.1 Enhanced Exit Manager
```python
class ProfessionalExitManager:
    def __init__(self):
        self.exit_rules = {
            'PRIMARY': {
                'profit_target': 0.50,
                'stop_loss': 1.50,
                'time_stop_dte': 21,
                'delta_breach': 0.30
            },
            'INCOME_POP': {
                'profit_target': 0.25,
                'stop_loss': 1.00,
                'time_stop_dte': 0,
                'delta_breach': None
            }
        }
        
    def check_exits(self, position):
        rules = self.exit_rules[position.book_type]
        
        # Profit target
        if position.current_pnl_pct >= rules['profit_target']:
            return True, "Profit target reached"
            
        # Stop loss
        if position.current_pnl_pct <= -rules['stop_loss']:
            return True, "Stop loss triggered"
            
        # Time stop
        if position.dte <= rules['time_stop_dte']:
            return True, "Time stop triggered"
            
        # Delta breach
        if rules['delta_breach'] and position.short_delta > rules['delta_breach']:
            return True, "Delta breach"
            
        return False, None
```

#### 3.2 VIX Hedge Implementation
```python
class VIXHedgeManager:
    def __init__(self):
        self.hedge_delta = 0.30
        self.size_pct = 0.015  # 1.5% of portfolio
        
    def calculate_hedge_size(self, portfolio_value, current_vix):
        if current_vix < 15:
            return portfolio_value * 0.02  # 2% in low vol
        elif current_vix > 25:
            return portfolio_value * 0.01  # 1% in high vol
        else:
            return portfolio_value * self.size_pct
            
    def select_vix_strike(self, current_vix):
        # 30-delta call approximately 20% OTM
        return round(current_vix * 1.20)
```

### Week 6: Integration & Enhanced Claude Prompt

#### 3.3 Strategy Orchestrator
```python
class StrategyOrchestrator:
    def __init__(self):
        self.analyzer = ProfessionalTradeAnalyzer()
        self.book_manager = MultiBookManager()
        self.position_sizer = DynamicPositionSizer()
        self.greeks_manager = PortfolioGreeksManager()
        self.exit_manager = ProfessionalExitManager()
        self.hedge_manager = VIXHedgeManager()
        
    async def generate_trades(self, market_data):
        # Check blackout windows
        if self.in_blackout_window():
            return []
            
        trades = []
        
        # Analyze each symbol
        for symbol in market_data:
            opportunity = self.analyzer.analyze_opportunity(symbol)
            if opportunity:
                # Route to appropriate book
                book = self.book_manager.route_trade(opportunity, symbol.iv_rank)
                
                # Size the position
                contracts = self.position_sizer.calculate_position_size(
                    opportunity.confidence,
                    opportunity.max_loss_per_contract,
                    book
                )
                
                if contracts > 0:
                    trades.append(self.build_trade_order(opportunity, contracts, book))
                    
        # Check for hedging needs
        if self.hedge_manager.needs_hedge():
            trades.append(self.build_hedge_order())
            
        return trades
```

## Phase 4: Testing & Validation (Weeks 7-8)

### Week 7: Parallel Testing

#### 4.1 A/B Testing Framework
```python
class StrategyComparison:
    def __init__(self):
        self.old_strategy = CurrentVolatilityStrategy()
        self.new_strategy = ProfessionalMultiBookStrategy()
        
    def run_parallel_test(self, market_data):
        # Run both strategies
        old_signals = self.old_strategy.analyze(market_data)
        new_signals = self.new_strategy.analyze(market_data)
        
        # Log for comparison
        self.log_comparison({
            'timestamp': datetime.now(),
            'old_trades': len(old_signals),
            'new_trades': len(new_signals),
            'old_exposure': self.calculate_exposure(old_signals),
            'new_exposure': self.calculate_exposure(new_signals),
            'differences': self.find_differences(old_signals, new_signals)
        })
```

#### 4.2 Gradual Rollout Schedule
```
Week 7, Days 1-3: 10% capital on new strategy
Week 7, Days 4-7: 25% capital if metrics positive
Week 8, Days 1-3: 50% capital if outperforming
Week 8, Days 4-7: 100% capital if all checks pass
```

### Week 8: Full Production Readiness

#### 4.3 Production Checklist
- [ ] All unit tests passing (>95% coverage)
- [ ] Integration tests with live data feeds
- [ ] Risk limits properly enforced
- [ ] Emergency stop functionality tested
- [ ] Rollback procedures documented
- [ ] Monitoring dashboards updated
- [ ] Alert system configured
- [ ] Team training completed

## Monitoring & Success Metrics

### Key Performance Indicators
1. **Trade Frequency**: 15-25 trades/month (vs current 1-2)
2. **Win Rate**: >85% (maintain high probability)
3. **Average P&L**: $200-300 per trade (vs current $50)
4. **Sharpe Ratio**: >2.0 (vs current ~0.5)
5. **Max Drawdown**: <10% (risk-controlled)

### Daily Monitoring Checklist
- [ ] Portfolio delta within ±0.30
- [ ] Day-at-risk below 10%
- [ ] All positions have stop losses
- [ ] VIX hedge active if required
- [ ] No blackout window violations

### Weekly Review Metrics
- Gross theta generation
- P&L by strategy book
- P&L by symbol
- Win rate by confidence tier
- Average days in trade
- Risk-adjusted returns

## Rollback Procedures

### Emergency Rollback Plan
1. **Immediate** (0-1 hour):
   - Activate kill switch
   - Stop all new trades
   - Alert team

2. **Day 1**:
   - Close all Income-Pop positions
   - Reduce Primary book by 50%
   - Revert to old strategy for new trades

3. **Day 2-5**:
   - Systematically close remaining positions
   - Document issues encountered
   - Post-mortem analysis

4. **Day 5+**:
   - Full system restore
   - Address identified issues
   - Plan remediation

## Implementation Timeline Summary

| Week | Phase | Key Deliverables |
|------|-------|-----------------|
| 1-2 | Foundation | Data feeds, database schema, backtesting |
| 3-4 | Core Logic | Strategy selection, position sizing, risk management |
| 5-6 | Advanced | Exit management, VIX hedging, integration |
| 7 | Testing | Parallel testing, gradual rollout begins |
| 8 | Production | Full rollout, monitoring, optimization |

## Next Steps

1. **Immediate Actions**:
   - Set up technical indicator calculations
   - Expand universe to include XLE, XLK, DIA
   - Create Greeks data pipeline

2. **Week 1 Priorities**:
   - Implement RSI/SMA calculations
   - Add delta-based strike selection
   - Update backtesting with new rules

3. **Validation Requirements**:
   - Backtest on 2 years of data
   - Paper trade for 2 weeks minimum
   - Compare results vs current strategy

## Risk Considerations

### Technical Risks
- Data feed reliability
- Greeks calculation accuracy
- Order execution latency

### Market Risks
- Regime changes
- Correlation breakdowns
- Liquidity issues

### Mitigation Strategies
- Redundant data sources
- Conservative position limits initially
- Extensive backtesting across market regimes

## Conclusion

This migration represents a significant upgrade in sophistication and expected performance. By following this structured approach, we can minimize risks while maximizing the probability of successful implementation.

The new strategy should deliver:
- 10-20x increase in returns
- Better risk-adjusted performance
- More consistent income generation
- Professional-grade risk management

With careful execution of this plan, we'll transform from a basic volatility strategy to an institutional-quality options income system.