#!/usr/bin/env python3
"""Check current Lighter DEX positions"""

import asyncio
import os
from dotenv import load_dotenv
from dexes.lighter.adapter import LighterAdapter

load_dotenv()

async def main():
    # Get credentials from env
    api_key_private = os.getenv('LIGHTER_API_KEY_PRIVATE')
    api_key_public = os.getenv('LIGHTER_API_KEY_PUBLIC')
    account_index = int(os.getenv('LIGHTER_ACCOUNT_INDEX', 341823))
    api_key_index = int(os.getenv('LIGHTER_API_KEY_INDEX', 2))

    adapter = LighterAdapter(
        api_key_private=api_key_private,
        api_key_public=api_key_public,
        account_index=account_index,
        api_key_index=api_key_index
    )

    await adapter.initialize()
    positions = await adapter.get_positions()

    print('\n=== CURRENT LIGHTER POSITIONS ===')
    print(f'{"Symbol":<10} {"Size":<15} {"Side":<6} {"Entry":<12} {"PnL":<10}')
    print('-' * 60)

    total_pnl = 0
    for pos in positions:
        symbol = pos.get('symbol', 'Unknown')
        size = pos.get('size', 0)
        side = pos.get('side', 'Unknown')
        entry_price = pos.get('entry_price', 0)
        pnl = pos.get('pnl', 0)
        total_pnl += pnl

        print(f'{symbol:<10} {size:<15.4f} {side:<6} ${entry_price:<11.4f} ${pnl:>8.2f}')

    print('-' * 60)
    print(f'Total positions: {len(positions)}')
    print(f'Total PnL: ${total_pnl:.2f}\n')

if __name__ == '__main__':
    asyncio.run(main())
