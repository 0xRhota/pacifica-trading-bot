#!/usr/bin/env python3
"""
Place a single small test order on Pacifica using SDK
"""

import asyncio
import os
from dotenv import load_dotenv
from pacifica_sdk import PacificaSDK
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig

# Load environment variables
load_dotenv()

async def main():
    """Place test order"""
    print("="*60)
    print("⚠️  LIVE ORDER TEST - REAL MONEY")
    print("="*60)

    # Get private key from environment
    private_key = os.getenv("SOLANA_PRIVATE_KEY")

    if not private_key:
        print("❌ Error: SOLANA_PRIVATE_KEY not found in .env file")
        print("\nPlease create a .env file with:")
        print("SOLANA_PRIVATE_KEY=your_base58_private_key_here")
        return

    print(f"Using account: {BotConfig.ACCOUNT_ADDRESS}")
    print()

    # Get current market data
    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL
    )

    async with PacificaAPI(config) as api:
        # Get account info
        print("📊 Getting account info...")
        account = await api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
        if not account:
            print("❌ Could not get account info")
            return

        balance = float(account.get('balance', 0))
        equity = float(account.get('account_equity', 0))
        print(f"💰 Balance: ${balance:.2f}")
        print(f"💰 Equity: ${equity:.2f}")

        # Get current SOL price
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
    print(f"   Estimated Price: ${price:.2f}")
    print()

    # Confirm
    response = input("Type 'yes' to place this REAL order: ").strip().lower()
    if response != 'yes':
        print("❌ Cancelled")
        return

    # Initialize SDK
    print("\n🔐 Initializing Pacifica SDK...")
    sdk = PacificaSDK(private_key, BotConfig.BASE_URL)
    print(f"✅ Connected as: {sdk.get_account_address()}")

    # Verify it matches
    if sdk.get_account_address() != BotConfig.ACCOUNT_ADDRESS:
        print(f"⚠️  WARNING: SDK address doesn't match config!")
        print(f"   SDK: {sdk.get_account_address()}")
        print(f"   Config: {BotConfig.ACCOUNT_ADDRESS}")
        confirm = input("Continue anyway? (yes/no): ").strip().lower()
        if confirm != 'yes':
            return

    # Place order
    print("\n🚀 Placing market order...")
    try:
        result = sdk.create_market_order(
            symbol=symbol,
            side="bid",  # bid = buy/long
            amount=f"{size:.6f}",
            slippage_percent="1.0"  # 1% slippage tolerance
        )

        print("\n" + "="*60)
        print("📥 ORDER RESPONSE:")
        print("="*60)

        if isinstance(result, dict):
            if result.get('success'):
                print("✅ ORDER PLACED SUCCESSFULLY!")
                print(f"\nResponse: {result}")
            else:
                print("❌ ORDER FAILED")
                print(f"\nResponse: {result}")
        else:
            print(f"Response: {result}")

        print("\n" + "="*60)

        if result.get('success'):
            print("\n🎉 Success! Check the Pacifica UI to see your position.")
            print("⚠️  Remember to manually close it when ready!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
