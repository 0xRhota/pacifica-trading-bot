#!/usr/bin/env python3
"""
Live testing script for Pacifica bot
Tests with real API but doesn't place trades unless confirmed
"""

import asyncio
import logging
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig
from strategies import VolumeStrategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_live_data():
    """Test live market data retrieval"""
    print("="*60)
    print("🔴 PACIFICA LIVE DATA TEST")
    print("="*60)

    if not BotConfig.API_KEY:
        print("❌ No API key found! Please set PACIFICA_API_KEY in .env or config.py")
        return False

    print(f"API Key: {BotConfig.API_KEY[:10]}...{BotConfig.API_KEY[-4:]}")
    print(f"Base URL: {BotConfig.BASE_URL}")
    print()

    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=BotConfig.TRADING_SYMBOLS
    )

    async with PacificaAPI(config) as api:
        print("📊 Testing Account Info...")
        try:
            account = await api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
            if account:
                print(f"✅ Account retrieved:")
                for key, value in account.items():
                    print(f"   {key}: {value}")
                print()
            else:
                print("❌ Failed to get account info - check API key/permissions")
                return False
        except Exception as e:
            print(f"❌ Account info error: {e}")
            return False

        print("📈 Testing Market Data...")
        for symbol in BotConfig.TRADING_SYMBOLS:
            print(f"\n  {symbol}:")

            # Get price
            try:
                price = await api.get_market_price(symbol)
                if price:
                    print(f"    Price: ${price:,.2f}")
                else:
                    print(f"    ❌ No price data")
                    continue
            except Exception as e:
                print(f"    ❌ Price error: {e}")
                continue

            # Get orderbook
            try:
                orderbook = await api.get_orderbook(symbol)
                if orderbook and "bids" in orderbook and "asks" in orderbook:
                    bids = orderbook.get("bids", [])
                    asks = orderbook.get("asks", [])

                    if bids and asks:
                        best_bid = float(bids[0][0])
                        best_ask = float(asks[0][0])
                        spread = best_ask - best_bid
                        spread_pct = (spread / best_bid) * 100

                        print(f"    Best Bid: ${best_bid:,.2f}")
                        print(f"    Best Ask: ${best_ask:,.2f}")
                        print(f"    Spread: ${spread:.2f} ({spread_pct:.4f}%)")

                        # Check orderbook depth
                        bid_volume = sum(float(b[1]) for b in bids[:5])
                        ask_volume = sum(float(a[1]) for a in asks[:5])
                        print(f"    Bid Volume (top 5): {bid_volume:.4f}")
                        print(f"    Ask Volume (top 5): {ask_volume:.4f}")
                    else:
                        print(f"    ❌ Empty orderbook")
                else:
                    print(f"    ❌ No orderbook data")
            except Exception as e:
                print(f"    ❌ Orderbook error: {e}")

    print("\n" + "="*60)
    print("✅ Live data test complete!")
    print("="*60)
    return True

async def test_strategy_signals():
    """Test strategy signal generation with live data"""
    print("\n" + "="*60)
    print("🎯 TESTING STRATEGY SIGNALS")
    print("="*60)

    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=BotConfig.TRADING_SYMBOLS
    )

    async with PacificaAPI(config) as api:
        strategy = VolumeStrategy(api)

        print("\nGenerating signals for all symbols...")
        signals = await strategy.generate_signals(BotConfig.TRADING_SYMBOLS)

        if signals:
            print(f"\n✅ Generated {len(signals)} signals:")
            for signal in signals:
                print(f"\n  {signal.symbol}:")
                print(f"    Side: {signal.side.upper()}")
                print(f"    Size: {signal.size:.6f}")
                print(f"    Confidence: {signal.confidence:.2%}")
                print(f"    Reason: {signal.reason}")
        else:
            print("\n⚠️  No signals generated (may need to wait for cooldown or better market conditions)")

    print("\n" + "="*60)
    return True

async def test_position_simulation():
    """Simulate what trades would look like without actually placing them"""
    print("\n" + "="*60)
    print("🎲 SIMULATING POTENTIAL TRADES")
    print("="*60)

    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=BotConfig.TRADING_SYMBOLS
    )

    async with PacificaAPI(config) as api:
        for symbol in BotConfig.TRADING_SYMBOLS:
            price = await api.get_market_price(symbol)
            if not price:
                continue

            # Simulate position sizes
            import random
            position_value = random.uniform(40, 100)
            size = position_value / price

            print(f"\n  {symbol}:")
            print(f"    Current Price: ${price:,.2f}")
            print(f"    Position Value: ${position_value:.2f}")
            print(f"    Size: {size:.6f}")
            print(f"    Side: BUY (longs only)")

            # Simulate fees (assuming 0.05% taker fee)
            fee_pct = 0.0005
            entry_fee = position_value * fee_pct
            exit_fee = position_value * fee_pct
            total_fees = entry_fee + exit_fee

            # Simulate profit targets
            min_profit_pct = BotConfig.MIN_PROFIT_THRESHOLD
            max_loss_pct = BotConfig.MAX_LOSS_THRESHOLD

            target_price = price * (1 + min_profit_pct)
            stop_price = price * (1 - max_loss_pct)

            print(f"    Entry Fee: ${entry_fee:.4f}")
            print(f"    Exit Fee: ${exit_fee:.4f}")
            print(f"    Total Fees: ${total_fees:.4f}")
            print(f"    Target Price: ${target_price:,.2f} (+{min_profit_pct:.2%})")
            print(f"    Stop Price: ${stop_price:,.2f} (-{max_loss_pct:.2%})")

    print("\n" + "="*60)
    return True

async def main():
    """Run all live tests"""
    print("\n🚀 Starting Pacifica Live Testing Suite\n")

    tests = [
        ("Live Data Retrieval", test_live_data),
        ("Strategy Signal Generation", test_strategy_signals),
        ("Position Simulation", test_position_simulation),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = "✅ PASSED" if result else "❌ FAILED"
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = "❌ ERROR"

        await asyncio.sleep(1)  # Brief pause between tests

    # Print summary
    print("\n" + "="*60)
    print("📋 LIVE TEST SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        print(f"{test_name:30} | {result}")

    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len(results)

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All live tests passed! Bot can connect and analyze markets.")
        print("\n⚠️  To actually trade, run: python main.py")
    else:
        print("\n⚠️  Some tests failed. Check API configuration.")

if __name__ == "__main__":
    asyncio.run(main())
