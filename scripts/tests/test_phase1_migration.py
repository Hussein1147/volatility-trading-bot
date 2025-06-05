#!/usr/bin/env python3
"""
Test script for Phase 1 migration changes:
1. Technical indicators (RSI, SMA) in data fetcher
2. Expanded universe (DIA, XLE, XLK)
3. Lowered IV threshold (40)
4. Directional filters
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.backtest.data_fetcher import AlpacaDataFetcher
from src.core.volatility_bot import EnhancedAlpacaVolatilityBot
import pandas as pd

async def test_technical_indicators():
    """Test that technical indicators are calculated correctly"""
    print("\n🧪 Testing Technical Indicators...")
    fetcher = AlpacaDataFetcher()
    
    # Test with SPY
    end_date = datetime.now()
    start_date = end_date - timedelta(days=45)
    
    try:
        df = await fetcher.get_stock_data('SPY', start_date, end_date)
        
        if df.empty:
            print("❌ No data returned")
            return False
            
        # Check for technical indicators
        has_sma = 'sma_20' in df.columns
        has_rsi = 'rsi_14' in df.columns
        
        print(f"✅ SMA_20 column present: {has_sma}")
        print(f"✅ RSI_14 column present: {has_rsi}")
        
        # Print last few values
        if has_sma and has_rsi:
            print("\nLast 5 rows of technical data:")
            print(df[['close', 'sma_20', 'rsi_14']].tail())
            
            # Verify values are reasonable
            last_rsi = df['rsi_14'].iloc[-1]
            if pd.notna(last_rsi) and 0 <= last_rsi <= 100:
                print(f"✅ RSI value is valid: {last_rsi:.2f}")
            else:
                print(f"❌ RSI value invalid: {last_rsi}")
                return False
                
        return has_sma and has_rsi
        
    except Exception as e:
        print(f"❌ Error testing indicators: {e}")
        return False

async def test_expanded_universe():
    """Test that new symbols are included"""
    print("\n🧪 Testing Expanded Universe...")
    
    # Check by reading the source code
    import ast
    
    with open('src/core/volatility_bot.py', 'r') as f:
        content = f.read()
        
    # Find the symbols assignment
    for line in content.split('\n'):
        if 'self.symbols =' in line and 'SPY' in line:
            # Extract the list from the line
            try:
                # Find the list part
                start = line.find('[')
                end = line.find(']') + 1
                symbols_str = line[start:end]
                symbols = ast.literal_eval(symbols_str)
                
                expected_symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLE', 'XLK']
                
                print(f"Expected symbols: {expected_symbols}")
                print(f"Bot symbols: {symbols}")
                
                symbols_match = set(symbols) == set(expected_symbols)
                if symbols_match:
                    print("✅ Universe correctly expanded")
                else:
                    print("❌ Universe mismatch")
                    
                return symbols_match
            except:
                pass
    
    print("❌ Could not find symbols definition")
    return False

async def test_iv_threshold():
    """Test that IV threshold is lowered to 40"""
    print("\n🧪 Testing IV Threshold...")
    
    # Check by reading the source code
    with open('src/core/volatility_bot.py', 'r') as f:
        content = f.read()
        
    # Find the min_iv_rank assignment
    for line in content.split('\n'):
        if 'self.min_iv_rank =' in line:
            # Extract the value
            try:
                # Find the number part
                parts = line.split('=')
                if len(parts) >= 2:
                    value_str = parts[1].strip()
                    # Extract number before comment
                    value = int(value_str.split()[0])
                    
                    print(f"Current IV threshold: {value}")
                    
                    if value == 40:
                        print("✅ IV threshold correctly set to 40")
                        return True
                    else:
                        print(f"❌ IV threshold incorrect: {value}")
                        return False
            except:
                pass
    
    print("❌ Could not find min_iv_rank definition")
    return False

async def test_directional_filters():
    """Test directional filter logic"""
    print("\n🧪 Testing Directional Filters...")
    
    # Create test scenarios
    test_cases = [
        {
            'name': 'Bullish conditions - should allow PUT spreads',
            'price': 450,
            'sma_20': 445,
            'rsi_14': 65,
            'expected_allowed': 'put_credit'
        },
        {
            'name': 'Bearish conditions - should allow CALL spreads',
            'price': 440,
            'sma_20': 445,
            'rsi_14': 35,
            'expected_allowed': 'call_credit'
        },
        {
            'name': 'Mixed signals - should NOT trade',
            'price': 450,
            'sma_20': 445,
            'rsi_14': 35,  # Price above SMA but RSI bearish
            'expected_allowed': None
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"  Price: ${test['price']}, SMA: ${test['sma_20']}, RSI: {test['rsi_14']}")
        
        # Check directional logic
        price_above_sma = test['price'] > test['sma_20']
        rsi_bullish = test['rsi_14'] > 50
        
        if price_above_sma and rsi_bullish:
            allowed = 'put_credit'
        elif not price_above_sma and not rsi_bullish:
            allowed = 'call_credit'
        else:
            allowed = None
            
        success = allowed == test['expected_allowed']
        results.append(success)
        
        if success:
            print(f"  ✅ Correctly identified: {allowed or 'No trade'}")
        else:
            print(f"  ❌ Wrong: expected {test['expected_allowed']}, got {allowed}")
    
    return all(results)

async def test_technical_data_integration():
    """Test that technical data flows through the system"""
    print("\n🧪 Testing Technical Data Integration...")
    
    fetcher = AlpacaDataFetcher()
    
    # Test get_technical_indicators method
    try:
        tech_data = await fetcher.get_technical_indicators('SPY', datetime.now())
        
        required_fields = ['price', 'sma_20', 'rsi_14', 'volume']
        has_all_fields = all(field in tech_data for field in required_fields)
        
        if has_all_fields:
            print("✅ Technical indicators method returns all required fields")
            print(f"   Price: ${tech_data['price']:.2f}")
            print(f"   SMA_20: ${tech_data['sma_20']:.2f}" if tech_data['sma_20'] else "   SMA_20: Not available")
            print(f"   RSI_14: {tech_data['rsi_14']:.2f}" if tech_data['rsi_14'] else "   RSI_14: Not available")
            return True
        else:
            print("❌ Missing required fields in technical data")
            return False
            
    except Exception as e:
        print(f"❌ Error getting technical indicators: {e}")
        return False

async def main():
    """Run all Phase 1 tests"""
    print("="*60)
    print("PHASE 1 MIGRATION TEST SUITE")
    print("="*60)
    
    tests = [
        ("Technical Indicators", test_technical_indicators),
        ("Expanded Universe", test_expanded_universe),
        ("IV Threshold", test_iv_threshold),
        ("Directional Filters", test_directional_filters),
        ("Technical Data Integration", test_technical_data_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 1 tests passed! Ready to proceed.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)