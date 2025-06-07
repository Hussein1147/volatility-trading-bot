#!/usr/bin/env python3
"""
Test Alpaca paper trading connectivity and options trading capability
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

load_dotenv()

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass

def test_paper_trading():
    """Test paper trading connectivity"""
    print("🔍 Testing Alpaca Paper Trading Connectivity")
    print("=" * 60)
    
    # Check environment variables
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    if not api_key or not secret_key:
        print("❌ Missing ALPACA_API_KEY or ALPACA_SECRET_KEY")
        return False
    
    print(f"✅ API credentials found")
    print(f"📍 Base URL: {base_url}")
    
    # Ensure we're using paper trading URL
    if 'paper' not in base_url:
        print("⚠️  WARNING: Not using paper trading URL!")
        print("    Set ALPACA_BASE_URL=https://paper-api.alpaca.markets")
    
    try:
        # Initialize trading client
        trading_client = TradingClient(api_key, secret_key, paper=True)
        
        # Get account info
        account = trading_client.get_account()
        print(f"\n✅ Connected to Alpaca Paper Trading")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"   Options Trading Level: {account.options_trading_level}")
        
        # Check if options trading is enabled
        if account.options_trading_level and int(account.options_trading_level) > 0:
            print(f"✅ Options trading enabled (Level {account.options_trading_level})")
        else:
            print("❌ Options trading NOT enabled!")
            print("   Please enable options trading in your Alpaca paper account")
        
        # Test getting option assets
        print("\n🔍 Testing options data access...")
        request = GetAssetsRequest(asset_class=AssetClass.US_OPTION)
        
        try:
            options = trading_client.get_all_assets(request)
            option_count = len(list(options))
            print(f"✅ Options data accessible ({option_count:,} option contracts found)")
        except Exception as e:
            print(f"❌ Cannot access options data: {e}")
            print("   This might be normal if your account doesn't have options access")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error connecting to Alpaca: {e}")
        return False

if __name__ == "__main__":
    success = test_paper_trading()
    print("\n" + "=" * 60)
    if success:
        print("✅ Paper trading connectivity test PASSED")
        print("\n📝 Next Steps:")
        print("1. Ensure options trading is enabled in your paper account")
        print("2. Start the main dashboard to begin paper trading")
        print("3. Monitor trades in the dashboard")
    else:
        print("❌ Paper trading connectivity test FAILED")
        print("\n📝 Troubleshooting:")
        print("1. Check your .env file has correct API keys")
        print("2. Ensure ALPACA_BASE_URL is set to paper trading URL")
        print("3. Verify your API keys at https://app.alpaca.markets")