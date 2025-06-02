#!/usr/bin/env python3
"""
Comprehensive system verification script
"""

import sys
import os
import asyncio
import subprocess
import time
import requests
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

class SystemVerifier:
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.errors = []
        
    def check(self, name, func):
        """Run a check and track results"""
        try:
            result = func()
            if result:
                print(f"   ✅ {name}")
                self.checks_passed += 1
            else:
                print(f"   ❌ {name}")
                self.checks_failed += 1
                self.errors.append(name)
        except Exception as e:
            print(f"   ❌ {name}: {str(e)[:100]}")
            self.checks_failed += 1
            self.errors.append(f"{name}: {str(e)[:50]}")
            
    async def check_async(self, name, func):
        """Run an async check and track results"""
        try:
            result = await func()
            if result:
                print(f"   ✅ {name}")
                self.checks_passed += 1
            else:
                print(f"   ❌ {name}")
                self.checks_failed += 1
                self.errors.append(name)
        except Exception as e:
            print(f"   ❌ {name}: {str(e)[:100]}")
            self.checks_failed += 1
            self.errors.append(f"{name}: {str(e)[:50]}")

def check_imports():
    """Test all critical imports"""
    try:
        # Core modules
        from src.core.trade_manager import EnhancedTradeManager
        from src.core.volatility_bot import EnhancedAlpacaVolatilityBot
        from src.core.position_tracker import PositionTracker
        
        # Data modules
        from src.data.trade_db import trade_db
        from src.data.simulated_pnl import simulated_tracker
        from src.data.database import DatabaseManager
        
        # UI modules
        from src.ui.dashboard import main as dashboard_main
        from src.ui.backtest_dashboard import main as backtest_main
        
        # Backtest modules
        from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
        from src.backtest.data_fetcher import AlpacaDataFetcher
        from src.backtest.visualizer import BacktestVisualizer
        
        return True
    except ImportError as e:
        print(f"      Import error: {e}")
        return False

def check_environment():
    """Check environment variables"""
    required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'ANTHROPIC_API_KEY']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            
    if missing:
        print(f"      Missing: {', '.join(missing)}")
        return False
    return True

def check_database():
    """Test database connectivity"""
    try:
        from src.data.trade_db import trade_db
        
        # Test basic operations
        stats = trade_db.get_statistics()
        
        # Check if tables exist
        import sqlite3
        conn = sqlite3.connect('trade_history.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        required_tables = ['claude_analyses', 'trades', 'market_scans', 'bot_logs']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"      Missing tables: {', '.join(missing_tables)}")
            return False
            
        return True
    except Exception as e:
        print(f"      Database error: {e}")
        return False

async def check_claude_api():
    """Test Claude API with correct model"""
    try:
        from anthropic import AsyncAnthropic
        
        client = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'OK'"}]
        )
        
        return 'OK' in response.content[0].text
    except Exception as e:
        print(f"      Claude API error: {e}")
        return False

async def check_alpaca_api():
    """Test Alpaca API connectivity"""
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        
        client = StockHistoricalDataClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY')
        )
        
        request = StockBarsRequest(
            symbol_or_symbols='SPY',
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=5)
        )
        
        bars = client.get_stock_bars(request)
        return not bars.df.empty
    except Exception as e:
        print(f"      Alpaca API error: {e}")
        return False

def check_dashboard_process(port, name):
    """Check if a dashboard is running on a port"""
    try:
        response = requests.get(f'http://localhost:{port}', timeout=5)
        return response.status_code == 200
    except:
        return False

def launch_dashboard(script, port, name):
    """Launch a dashboard and verify it starts"""
    try:
        # Kill any existing process on the port
        subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", shell=True)
        time.sleep(2)
        
        # Start the dashboard
        env = os.environ.copy()
        env['STREAMLIT_SERVER_PORT'] = str(port)
        env['STREAMLIT_SERVER_HEADLESS'] = 'true'
        
        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        # Wait for startup
        time.sleep(8)
        
        # Check if accessible
        try:
            response = requests.get(f'http://localhost:{port}', timeout=5)
            if response.status_code == 200:
                print(f"      {name} running at http://localhost:{port}")
                return True
        except:
            pass
            
        # Check for errors
        if process.poll() is not None:
            _, stderr = process.communicate()
            print(f"      Process died: {stderr.decode()[:200]}")
            
        return False
    except Exception as e:
        print(f"      Launch error: {e}")
        return False

async def run_quick_backtest():
    """Run a minimal backtest to verify functionality"""
    try:
        from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
        
        config = BacktestConfig(
            start_date=datetime.now() - timedelta(days=3),
            end_date=datetime.now(),
            symbols=['SPY'],
            initial_capital=10000,
            min_price_move=5.0,  # Very high to avoid trades
            confidence_threshold=90
        )
        
        engine = BacktestEngine(config)
        
        # Mock the Claude analysis to avoid API calls
        async def mock_analyze(market_data):
            return None
        
        engine._claude_analysis = mock_analyze
        
        results = await engine.run_backtest()
        return len(results.equity_curve) > 0
    except Exception as e:
        print(f"      Backtest error: {e}")
        return False

def check_project_structure():
    """Verify project structure is organized"""
    expected_structure = {
        'src/': ['__init__.py', 'core/', 'data/', 'ui/', 'backtest/'],
        'src/core/': ['__init__.py', 'trade_manager.py', 'volatility_bot.py', 'position_tracker.py'],
        'src/data/': ['__init__.py', 'trade_db.py', 'simulated_pnl.py', 'database.py'],
        'src/ui/': ['__init__.py', 'dashboard.py', 'backtest_dashboard.py'],
        'src/backtest/': ['__init__.py', 'backtest_engine.py', 'data_fetcher.py', 'visualizer.py'],
        'scripts/': ['verify_system.py'],
        'tests/': ['__init__.py', 'test_core.py', 'test_simple.py', 'test_suite.py'],
        'docs/': ['CLAUDE.md', 'DEPLOYMENT.md', 'LIVE_TRADING_SETUP.md', 'RECENT_CHANGES.md', 'TRADING_WORKFLOW.md']
    }
    
    missing = []
    for dir_path, expected_files in expected_structure.items():
        if not os.path.exists(dir_path):
            missing.append(dir_path)
        else:
            for file in expected_files:
                if not os.path.exists(os.path.join(dir_path, file)):
                    missing.append(os.path.join(dir_path, file))
    
    if missing:
        print(f"      Missing: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
        return False
    return True

async def main():
    print("🔍 VOLATILITY TRADING BOT SYSTEM VERIFICATION")
    print("=" * 60)
    
    verifier = SystemVerifier()
    
    # 1. Basic checks
    print("\n1. Basic System Checks")
    print("-" * 30)
    verifier.check("Python version >= 3.8", lambda: sys.version_info >= (3, 8))
    verifier.check("Virtual environment active", lambda: sys.prefix != sys.base_prefix)
    verifier.check("Project structure", check_project_structure)
    
    # 2. Dependencies
    print("\n2. Dependencies & Imports")
    print("-" * 30)
    verifier.check("All imports working", check_imports)
    verifier.check("Environment variables", check_environment)
    
    # 3. Database
    print("\n3. Database")
    print("-" * 30)
    verifier.check("SQLite database", check_database)
    
    # 4. External APIs
    print("\n4. External APIs")
    print("-" * 30)
    await verifier.check_async("Claude API (claude-sonnet-4-20250514)", check_claude_api)
    await verifier.check_async("Alpaca API", check_alpaca_api)
    
    # 5. Core functionality
    print("\n5. Core Functionality")
    print("-" * 30)
    await verifier.check_async("Backtest engine", run_quick_backtest)
    
    # 6. Dashboards
    print("\n6. Dashboards")
    print("-" * 30)
    
    # Check if already running
    main_running = check_dashboard_process(8501, "Main Dashboard")
    backtest_running = check_dashboard_process(8502, "Backtest Dashboard")
    
    if main_running:
        print("   ✅ Main Dashboard already running at http://localhost:8501")
        verifier.checks_passed += 1
    else:
        print("   ⏳ Launching Main Dashboard...")
        if launch_dashboard('run_dashboard.py', 8501, "Main Dashboard"):
            verifier.checks_passed += 1
        else:
            verifier.checks_failed += 1
            verifier.errors.append("Main Dashboard launch failed")
    
    if backtest_running:
        print("   ✅ Backtest Dashboard already running at http://localhost:8502")
        verifier.checks_passed += 1
    else:
        print("   ⏳ Launching Backtest Dashboard...")
        if launch_dashboard('run_backtest.py', 8502, "Backtest Dashboard"):
            verifier.checks_passed += 1
        else:
            verifier.checks_failed += 1
            verifier.errors.append("Backtest Dashboard launch failed")
    
    # Final summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total checks: {verifier.checks_passed + verifier.checks_failed}")
    print(f"Passed: {verifier.checks_passed}")
    print(f"Failed: {verifier.checks_failed}")
    
    if verifier.errors:
        print("\n❌ ERRORS:")
        for error in verifier.errors:
            print(f"   - {error}")
    else:
        print("\n✅ ALL CHECKS PASSED!")
        print("\nDashboards:")
        print("   Main Dashboard: http://localhost:8501")
        print("   Backtest Dashboard: http://localhost:8502")
    
    return verifier.checks_failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)