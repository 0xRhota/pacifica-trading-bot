#!/usr/bin/env python3
"""
Live trade test - place one small position to verify everything works
"""

import asyncio
import logging
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def place_test_trade():
    """Place a single small test trade"""
    print("="*60)
    print("⚠️  LIVE TRADE TEST - REAL MONEY")
    print("="*60)
    print(f"This will place a REAL trade with REAL money!")
    print(f"Position size: ~$5-8")
    print(f"Symbol: SOL (most liquid)")
    print()

    response = input("Type 'yes' to continue: ").strip().lower()
    if response != 'yes':
        print("❌ Cancelled")
        return

    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=["SOL"]
    )

    async with PacificaAPI(config) as api:
        # Get account info
        print("\n📊 Getting account info...")
        account = await api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
        if not account:
            print("❌ Could not get account info")
            return

        balance = float(account.get('balance', 0))
        equity = float(account.get('account_equity', 0))
        print(f"💰 Balance: ${balance:.2f}")
        print(f"💰 Equity: ${equity:.2f}")

        # Get current price
        print("\n📈 Getting SOL price...")
        symbol = "SOL"
        price = await api.get_market_price(symbol)
        if not price:
            print("❌ Could not get price")
            return

        print(f"Current SOL price: ${price:.2f}")

        # Calculate small position
        position_value = 6.0  # $6 position
        size = position_value / price

        print(f"\n📝 Order Details:")
        print(f"   Symbol: {symbol}")
        print(f"   Side: BUY (long)")
        print(f"   Size: {size:.6f} SOL")
        print(f"   Value: ${position_value:.2f}")
        print(f"   Price: ${price:.2f}")
        print()

        final_confirm = input("Type 'PLACE ORDER' to execute: ").strip()
        if final_confirm != 'PLACE ORDER':
            print("❌ Cancelled")
            return

        # Place the order
        print("\n🚀 Placing order...")
        try:
            order = await api.create_market_order(symbol, "buy", size)

            if order:
                print("\n✅ ORDER PLACED!")
                print(f"Order response: {order}")
                print()
                print("🎉 Success! You should see this position in the Pacifica UI now.")
                print("⚠️  Remember to manually close it when you're ready!")
            else:
                print("\n❌ Order failed - no response from API")

        except Exception as e:
            print(f"\n❌ Error placing order: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(place_test_trade())
