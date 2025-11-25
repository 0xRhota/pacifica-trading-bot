#!/usr/bin/env python3
"""
Check what P&L data is available from Lighter account API
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dexes.lighter.lighter_sdk import LighterSDK

load_dotenv()


async def check_pnl():
    """Check what PnL data we can get from account API"""

    lighter_private_key = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
    lighter_account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823"))
    lighter_api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))

    sdk = LighterSDK(
        private_key=lighter_private_key,
        account_index=lighter_account_index,
        api_key_index=lighter_api_key_index
    )

    try:
        print("=" * 80)
        print("LIGHTER ACCOUNT P&L CHECK")
        print("=" * 80)
        print()

        # Get account balance
        balance = await sdk.get_balance()
        print(f"💰 Available Balance: ${balance:.2f}")
        print()

        # Get positions with PnL
        positions_result = await sdk.get_positions()

        if positions_result.get('success'):
            positions = positions_result.get('data', [])
            print(f"📊 Open Positions: {len(positions)}")
            print()

            if positions:
                print(f"{'Symbol':<10} {'Size':<12} {'Entry':<12} {'Current PnL':<15}")
                print("-" * 60)
                total_unrealized = 0
                for pos in positions:
                    symbol = pos.get('symbol', 'UNKNOWN')
                    size = pos.get('size', 0)
                    entry = pos.get('entry_price', 0)
                    pnl = pos.get('pnl', 0)
                    total_unrealized += pnl
                    print(f"{symbol:<10} {size:<12.4f} ${entry:<11.2f} ${pnl:<14.2f}")

                print()
                print(f"Total Unrealized P&L: ${total_unrealized:.2f}")
            else:
                print("No open positions")

            print()
            print("=" * 80)
            print()
            print("⚠️  NOTE: Account API only shows CURRENT positions (unrealized P&L)")
            print("   It does NOT provide:")
            print("   - Realized P&L from closed trades")
            print("   - Historical trade data")
            print("   - Win/loss statistics")
            print()
            print("📝 The CSV export shows -$34.60 realized P&L")
            print("   We need to find the API endpoint that provides this data")
            print()
            print("=" * 80)

    finally:
        await sdk.close()


if __name__ == '__main__':
    asyncio.run(check_pnl())
