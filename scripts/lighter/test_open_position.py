#!/usr/bin/env python3
"""
Test opening a new position on Lighter
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dexes.lighter.lighter_sdk import LighterSDK
from dotenv import load_dotenv

load_dotenv()

async def test_open_position():
    print("="*60)
    print("LIGHTER - OPEN TEST POSITION")
    print("="*60)

    # Initialize SDK
    sdk = LighterSDK(
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX"))
    )

    # Check current state
    print("\n📊 Current Status:")
    balance = await sdk.get_balance()
    print(f"   Balance: ${balance:.2f}")

    positions = await sdk.get_positions()
    if positions['success'] and positions['data']:
        print(f"   Existing positions: {len(positions['data'])}")
        for pos in positions['data']:
            print(f"      Market {pos['market_id']}: {pos['size']:.4f} @ ${pos['entry_price']:.2f}")
    else:
        print("   No existing positions")

    # Open new small position
    print("\n🟢 Opening new SOL position...")
    print("   Size: 0.050 SOL (minimum)")
    print("   Side: BUY (long)")
    print("   Type: Market order")

    result = await sdk.create_market_order(
        symbol="SOL",
        side="bid",  # BUY
        amount=0.050
    )

    if result['success']:
        print(f"\n✅ ORDER PLACED!")
        print(f"   TX Hash: {result['tx_hash'][:32]}...")
        print(f"   Message: {result['message']}")

        # Wait for execution
        print("\n⏳ Waiting 3 seconds for execution...")
        await asyncio.sleep(3)

        # Check new positions
        positions = await sdk.get_positions()
        if positions['success']:
            print("\n📊 Updated Positions:")
            for pos in positions['data']:
                symbol = {2: 'SOL', 1: 'BTC', 3: 'ETH'}.get(pos['market_id'], f"Market{pos['market_id']}")
                print(f"   {symbol}: {pos['size']:.4f} @ ${pos['entry_price']:.2f}")
                print(f"      Value: ${pos['value']:.2f}, P&L: ${pos['pnl']:.4f}")

        new_balance = await sdk.get_balance()
        print(f"\n💰 New Balance: ${new_balance:.2f} (was ${balance:.2f})")

    else:
        print(f"\n❌ ORDER FAILED: {result['error']}")

    await sdk.close()

    print("\n" + "="*60)
    print("Check position at: https://app.lighter.xyz")
    print("="*60)

asyncio.run(test_open_position())
