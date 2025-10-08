#!/usr/bin/env python3
"""
Place test order immediately (no confirmation prompt)
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from dexes.pacifica.pacifica_sdk import PacificaSDK
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig

load_dotenv()

async def main():
    print("="*60)
    print("🚀 PLACING LIVE ORDER")
    print("="*60)

    private_key = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key:
        print("❌ Error: SOLANA_PRIVATE_KEY not found in .env")
        return

    # Get market data
    config = TradingConfig(api_key=BotConfig.API_KEY, base_url=BotConfig.BASE_URL)

    async with PacificaAPI(config) as api:
        print("📊 Getting account info...")
        account = await api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
        balance = float(account.get('balance', 0))
        equity = float(account.get('account_equity', 0))

        print(f"💰 Balance: ${balance:.2f}")
        print(f"💰 Equity: ${equity:.2f}")

        print("\n📈 Getting SOL price...")
        symbol = "SOL"
        price = await api.get_market_price(symbol)
        print(f"Current SOL price: ${price:.2f}")

    # Calculate position (minimum $10 on Pacifica, must be multiple of 0.01)
    # Round UP to ensure we're over $10
    import math
    size = 10.5 / price
    size = math.ceil(size / 0.01) * 0.01  # Round UP to next 0.01
    actual_value = size * price

    print(f"\n📝 Order Details:")
    print(f"   Symbol: {symbol}")
    print(f"   Side: BUY (long)")
    print(f"   Size: {size:.6f} SOL")
    print(f"   Value: ${actual_value:.2f}")
    print(f"   Price: ${price:.2f}")

    # Initialize SDK
    print("\n🔐 Initializing SDK...")
    sdk = PacificaSDK(private_key, BotConfig.BASE_URL)
    print(f"✅ SDK Address: {sdk.get_account_address()}")

    # Place order
    print("\n🚀 PLACING ORDER NOW...")
    try:
        result = sdk.create_market_order(
            symbol=symbol,
            side="bid",  # bid = buy/long
            amount=f"{size:.6f}",
            slippage_percent="1.0"
        )

        print("\n" + "="*60)
        print("📥 ORDER RESPONSE:")
        print("="*60)

        import json
        print(json.dumps(result, indent=2))

        if result.get('success'):
            print("\n✅ ORDER PLACED SUCCESSFULLY!")
            print("🎉 Check Pacifica UI to see your position!")
        else:
            print("\n❌ ORDER FAILED")
            print(f"Error: {result}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
