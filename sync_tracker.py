#!/usr/bin/env python3
"""
Sync trade tracker with actual Pacifica API positions
This fixes stale "open" positions in the tracker
"""

import asyncio
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig
from trade_tracker import tracker

async def sync_tracker():
    """Sync tracker with actual API positions"""
    print("Syncing trade tracker with Pacifica API...")

    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=BotConfig.TRADING_SYMBOLS
    )

    async with PacificaAPI(config) as api:
        # Get actual open positions from API
        account = await api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
        if not account:
            print("❌ Could not get account info from API")
            return

        actual_positions = account.get('positions', [])
        actual_order_ids = set()

        if actual_positions:
            print(f"\n✅ Found {len(actual_positions)} actual open positions:")
            for pos in actual_positions:
                order_id = str(pos.get('order_id', ''))
                if order_id:
                    actual_order_ids.add(order_id)
                    print(f"  Order #{order_id}: {pos.get('symbol')} {pos.get('side')} {pos.get('size')}")
        else:
            print("\n✅ No open positions in Pacifica API")

        # Get tracker's open positions
        tracker_open = tracker.get_open_trades()
        tracker_order_ids = set(t['order_id'] for t in tracker_open if t.get('order_id'))

        print(f"\n📊 Tracker shows {len(tracker_open)} open positions:")
        for t in tracker_open:
            print(f"  Order #{t['order_id']}: {t['symbol']} {t['side']} {t['size']}")

        # Find positions that tracker thinks are open but aren't
        stale_positions = tracker_order_ids - actual_order_ids

        if stale_positions:
            print(f"\n⚠️  Found {len(stale_positions)} stale positions in tracker:")
            for order_id in stale_positions:
                # Find the trade
                for t in tracker_open:
                    if t['order_id'] == order_id:
                        symbol = t['symbol']
                        entry_price = t['entry_price']

                        # Get current price to estimate exit
                        current_price = await api.get_market_price(symbol)
                        if not current_price:
                            current_price = entry_price  # Fallback to entry

                        print(f"  Closing Order #{order_id} ({symbol}) in tracker...")
                        print(f"    Entry: ${entry_price:.2f}, Est. Exit: ${current_price:.2f}")

                        # Log exit in tracker
                        tracker.log_exit(
                            order_id=order_id,
                            exit_price=current_price,
                            exit_reason="Manual close (API sync)",
                            fees=0.0  # Can't determine actual fees
                        )
                        break

            print(f"\n✅ Synced {len(stale_positions)} positions")
        else:
            print("\n✅ Tracker is in sync with API!")

        # Print updated stats
        print("\n" + "="*60)
        tracker.print_stats()

if __name__ == "__main__":
    asyncio.run(sync_tracker())
