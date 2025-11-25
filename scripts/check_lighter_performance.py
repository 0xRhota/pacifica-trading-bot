"""
Get REAL performance data from Lighter exchange
Uses exchange API only - NO tracker JSON
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dexes.lighter.lighter_sdk import LighterSDK

load_dotenv()

async def get_real_performance():
    """Pull actual P&L from exchange"""

    # Use same account as bot (from env, defaults to 341823)
    account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823"))
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))

    sdk = LighterSDK(
        private_key=os.getenv("LIGHTER_PRIVATE_KEY"),
        account_index=account_index,
        api_key_index=api_key_index
    )

    print(f"🔍 Querying account {account_index} (API key {api_key_index})")
    print()

    try:
        # Get balance
        balance = await sdk.get_balance()

        # Get positions
        positions_resp = await sdk.get_positions()

        print("=" * 80)
        print("📊 LIGHTER EXCHANGE DATA (SOURCE OF TRUTH)")
        print("=" * 80)
        print(f"💰 Balance: ${balance:.2f}" if balance else "Balance: N/A")
        print()

        if positions_resp.get('success'):
            positions = positions_resp['data']
            print(f"📍 Open Positions: {len(positions)}")

            if positions:
                print()
                for pos in positions:
                    symbol = pos['symbol']
                    side = pos['side']
                    size = pos['size']
                    entry = pos['entry_price']
                    pnl = pos['pnl']
                    value = pos['value']

                    print(f"  {symbol:6} {side:5} | Size: {size:.4f} | Entry: ${entry:.2f} | P&L: ${pnl:.2f} | Value: ${value:.2f}")
            else:
                print("  None")
        else:
            print(f"⚠️ Error getting positions: {positions_resp.get('error')}")

        print()
        print("=" * 80)
        print("✅ All data from EXCHANGE API - tracker JSON ignored")
        print("=" * 80)

    finally:
        await sdk.close()

if __name__ == "__main__":
    asyncio.run(get_real_performance())
