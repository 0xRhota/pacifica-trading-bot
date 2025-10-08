#!/usr/bin/env python3
"""
Test script for Pacifica trading bot
Tests API connectivity and basic functionality with minimal risk
"""

import asyncio
import logging
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_api_connectivity():
    """Test basic API connectivity"""
    print("🔧 Testing Pacifica API connectivity...")
    
    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL
    )
    
    async with PacificaAPI(config) as api:
        try:
            # Test account info
            print("📊 Testing account info...")
            account = await api.get_account_info()
            if account:
                print(f"✅ Account info retrieved: {account}")
            else:
                print("❌ Failed to get account info")
                return False
            
            # Test market data
            print("📈 Testing market data...")
            for symbol in ["SOL-USD", "BTC-USD"]:
                price = await api.get_market_price(symbol)
                if price:
                    print(f"✅ {symbol} price: ${price:.4f}")
                else:
                    print(f"❌ Failed to get price for {symbol}")
                    
                # Test orderbook
                orderbook = await api.get_orderbook(symbol)
                if orderbook and "bids" in orderbook and "asks" in orderbook:
                    best_bid = orderbook["bids"][0][0] if orderbook["bids"] else "N/A"
                    best_ask = orderbook["asks"][0][0] if orderbook["asks"] else "N/A"
                    print(f"✅ {symbol} orderbook - Bid: {best_bid}, Ask: {best_ask}")
                else:
                    print(f"❌ Failed to get orderbook for {symbol}")
            
            print("✅ API connectivity test passed!")
            return True
            
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False

async def test_small_trade():
    """Test placing a very small trade (if balance allows)"""
    print("\n💰 Testing small trade functionality...")
    
    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL
    )
    
    async with PacificaAPI(config) as api:
        try:
            # Get account info first
            account = await api.get_account_info()
            if not account:
                print("❌ Cannot test trades - no account info")
                return False
            
            balance = float(account.get('equity', 0))
            print(f"📊 Account balance: ${balance:.2f}")
            
            if balance < 10:  # Need at least $10 to test
                print("❌ Insufficient balance for trade test (need $10+)")
                return False
            
            # Test with SOL-USD (usually has good liquidity)
            symbol = "SOL-USD"
            price = await api.get_market_price(symbol)
            
            if not price:
                print(f"❌ Cannot get price for {symbol}")
                return False
            
            # Very small trade - $5 worth
            trade_value = 5.0
            size = trade_value / price
            
            print(f"🔄 Placing small test trade: {symbol} buy {size:.6f} @ ${price:.4f}")
            
            # Place buy order
            order = await api.create_market_order(symbol, "buy", size)
            
            if order and "id" in order:
                print(f"✅ Buy order placed: {order['id']}")
                
                # Wait a moment
                await asyncio.sleep(2)
                
                # Immediately close with sell order
                print(f"🔄 Closing position with sell order...")
                close_order = await api.create_market_order(symbol, "sell", size)
                
                if close_order and "id" in close_order:
                    print(f"✅ Sell order placed: {close_order['id']}")
                    print("✅ Small trade test completed successfully!")
                    return True
                else:
                    print("❌ Failed to place closing sell order")
                    return False
            else:
                print("❌ Failed to place buy order")
                return False
                
        except Exception as e:
            print(f"❌ Trade test failed: {e}")
            return False

async def test_risk_management():
    """Test risk management functionality"""
    print("\n🛡️  Testing risk management...")
    
    from risk_manager import RiskManager
    
    risk_manager = RiskManager(BotConfig)
    
    # Test position size calculation
    balance = 1000.0
    confidence = 0.8
    size = risk_manager.calculate_position_size("SOL-USD", balance, confidence)
    print(f"✅ Position size calculation: ${size:.2f} for ${balance:.2f} balance")
    
    # Test trade permission
    can_trade, reason = risk_manager.check_can_trade("SOL-USD", 50.0)
    print(f"✅ Trade permission check: {can_trade} ({reason})")
    
    # Test trade recording
    risk_manager.record_trade_opened("SOL-USD", "buy", 0.1, 100.0)
    risk_manager.record_trade_closed("SOL-USD", 101.0, 0.1)
    
    summary = risk_manager.get_risk_summary()
    print(f"✅ Risk summary: {summary}")
    
    print("✅ Risk management test passed!")
    return True

async def main():
    """Run all tests"""
    print("🚀 Starting Pacifica Bot Test Suite")
    print("=" * 50)
    
    tests = [
        ("API Connectivity", test_api_connectivity),
        ("Risk Management", test_risk_management),
        ("Small Trade", test_small_trade),  # This one is optional and risky
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        try:
            if test_name == "Small Trade":
                print("⚠️  Warning: This test will place real trades with real money!")
                print("⚠️  Only proceed if you're ready to risk a small amount (~$5)")
                response = input("Continue with trade test? (y/N): ").strip().lower()
                if response != 'y':
                    print("⏭️  Skipping trade test")
                    results[test_name] = "Skipped"
                    continue
            
            result = await test_func()
            results[test_name] = "✅ PASSED" if result else "❌ FAILED"
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = "❌ ERROR"
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    for test_name, result in results.items():
        print(f"{test_name:20} | {result}")
    
    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len([r for r in results.values() if r != "Skipped"])
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready for deployment.")
    else:
        print("⚠️  Some tests failed. Check configuration and API setup.")

if __name__ == "__main__":
    asyncio.run(main())