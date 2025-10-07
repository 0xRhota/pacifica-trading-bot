#!/usr/bin/env python3
"""
Sync trade tracker with actual Pacifica API positions
This fixes stale "open" positions in the tracker
"""

import os
from pacifica_sdk import PacificaSDK
from config import BotConfig
from trade_tracker import tracker

def sync_tracker():
    """Sync tracker with actual API positions"""
    print("Syncing trade tracker with Pacifica API...")

    # Load private key
    with open('.env') as f:
        for line in f:
            if line.startswith('SOLANA_PRIVATE_KEY='):
                private_key = line.split('=', 1)[1].strip()
                break

    sdk = PacificaSDK(private_key, BotConfig.BASE_URL)

    # Get actual positions from API
    result = sdk.get_positions()
    if not result.get('success'):
        print("❌ Could not get positions from API")
        print(f"Error: {result}")
        return

    actual_positions = result.get('data', [])

    if actual_positions:
        print(f"\n✅ Found {len(actual_positions)} actual open positions:")
        for pos in actual_positions:
            symbol = pos.get('symbol')
            side = pos.get('side')
            amount = pos.get('amount')
            entry_price = pos.get('entry_price')
            print(f"  {symbol}: {side} {amount} @ ${entry_price}")
    else:
        print("\n✅ No open positions in Pacifica API")

    # Get tracker's open positions
    tracker_open = tracker.get_open_trades()

    print(f"\n📊 Tracker shows {len(tracker_open)} open positions:")
    for t in tracker_open:
        print(f"  Order #{t['order_id']}: {t['symbol']} {t['side']} {t['size']}")

    # Build a map of actual positions by symbol+side
    actual_map = {}
    for pos in actual_positions:
        symbol = pos.get('symbol')
        side = 'buy' if pos.get('side') == 'bid' else 'sell'
        amount = float(pos.get('amount'))
        key = f"{symbol}_{side}"
        actual_map[key] = {
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'entry_price': float(pos.get('entry_price'))
        }

    # For each tracker position, check if it still exists
    for t in tracker_open:
        symbol = t['symbol']
        side = t['side']
        order_id = t['order_id']
        key = f"{symbol}_{side}"

        # Check if this position type exists in actual positions
        if key not in actual_map:
            print(f"\n⚠️  Position {symbol} {side} (Order #{order_id}) is closed in API")
            print(f"  Closing in tracker...")

            # Close with no P&L (already closed elsewhere)
            tracker.log_exit(
                order_id=order_id,
                exit_price=t['entry_price'],  # Use entry price since we don't know
                exit_reason="Closed outside bot (API sync)",
                fees=0.0
            )

    print("\n✅ Sync complete!")
    print("\n" + "="*60)
    tracker.print_stats()

if __name__ == "__main__":
    sync_tracker()
