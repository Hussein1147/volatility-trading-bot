#!/usr/bin/env python3
"""Test backtest components before launching dashboard"""

import asyncio
import sys
import os
sys.path.insert(0, '.')
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

async def test_components():
    print("Testing Backtest Components\n" + "="*50)
    
    # Test 1: Import all modules
    print("\n1. Testing imports...")
    try:
        from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
        from src.backtest.data_fetcher import AlpacaDataFetcher
        from src.backtest.visualizer import BacktestVisualizer
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return
    
    # Test 2: Test Claude API with correct model
    print("\n2. Testing Claude API...")
    try:
        from anthropic import AsyncAnthropic
        anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        response = await anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": "Say 'API working' in JSON format: {\"status\": \"...\"}"}]
        )
        print(f"✅ Claude API working: {response.content[0].text}")
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        
    # Test 3: Simple backtest simulation
    print("\n3. Testing backtest engine...")
    try:
        config = BacktestConfig(
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            symbols=['SPY'],
            initial_capital=10000,
            min_price_move=3.0,  # High threshold to reduce trades
            confidence_threshold=80  # High threshold
        )
        
        engine = BacktestEngine(config)
        
        # Override the analyze method to avoid API calls during test
        async def mock_analyze(self, market_data):
            # Return None to simulate no trade signal
            return None
            
        # Replace the method
        engine._analyze_opportunity = mock_analyze.__get__(engine, BacktestEngine)
        
        print("   Running short backtest...")
        results = await engine.run_backtest()
        
        print(f"✅ Backtest completed")
        print(f"   Days processed: {len(results.equity_curve)}")
        print(f"   Final capital: ${results.equity_curve[-1]:,.2f}")
        
    except Exception as e:
        print(f"❌ Backtest error: {e}")
        import traceback
        traceback.print_exc()
        
    # Test 4: Visualization
    print("\n4. Testing visualization...")
    try:
        from src.backtest.visualizer import BacktestVisualizer
        from src.backtest.backtest_engine import BacktestResults
        
        # Create dummy results
        results = BacktestResults()
        results.equity_curve = [10000, 10100, 10050, 10200]
        results.total_trades = 0
        
        visualizer = BacktestVisualizer(results)
        fig = visualizer.plot_equity_curve()
        
        print("✅ Visualization created successfully")
        
    except Exception as e:
        print(f"❌ Visualization error: {e}")

if __name__ == "__main__":
    asyncio.run(test_components())