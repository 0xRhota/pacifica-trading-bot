#!/usr/bin/env python3
"""
Test the new get_trade_history() method from Lighter SDK
Verify it works and shows accurate P&L from exchange
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dexes.lighter.lighter_sdk import LighterSDK

load_dotenv()


async def test_trade_history():
    """Test fetching trade history from exchange"""

    print("=" * 80)
    print("LIGHTER TRADE HISTORY TEST (Exchange API)")
    print("=" * 80)
    print()

    # Initialize SDK
    lighter_private_key = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
    lighter_account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823"))
    lighter_api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))

    sdk = LighterSDK(
        private_key=lighter_private_key,
        account_index=lighter_account_index,
        api_key_index=lighter_api_key_index
    )

    try:
        # Fetch trade history (last 24 hours)
        print("📥 Fetching trade history from exchange API...")
        result = await sdk.get_trade_history(limit=500, hours=24)

        if not result.get('success'):
            print(f"❌ Error: {result.get('error')}")
            return

        # Print overall stats
        print()
        print("OVERALL PERFORMANCE (Last 24h):")
        print(f"  Total trades: {len(result['trades'])}")
        print(f"  Closed positions: {result['closed_count']}")
        print(f"  Wins: {result['wins']}")
        print(f"  Losses: {result['losses']}")
        print(f"  Win Rate: {result['win_rate']:.1f}%")
        print()
        print(f"  Total P&L: ${result['total_pnl']:.2f}")
        print(f"  Winning P&L: ${result['win_pnl']:.2f}")
        print(f"  Losing P&L: ${result['loss_pnl']:.2f}")

        if result['wins'] > 0:
            avg_win = result['win_pnl'] / result['wins']
            print(f"  Avg Win: ${avg_win:.2f}")

        if result['losses'] > 0:
            avg_loss = result['loss_pnl'] / result['losses']
            print(f"  Avg Loss: ${avg_loss:.2f}")

        print()

        # Per-symbol stats
        symbol_stats = result['symbol_stats']
        if symbol_stats:
            # Sort by P&L
            sorted_symbols = sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)

            print("TOP 15 PERFORMERS:")
            print(f"{'Symbol':<10} {'Closed':<7} {'Wins':<5} {'Losses':<7} {'Win%':<7} {'P&L':>10}")
            print("-" * 60)
            for symbol, stats in sorted_symbols[:15]:
                total = stats['trades']
                win_pct = (stats['wins'] / total * 100) if total > 0 else 0
                print(f"{symbol:<10} {total:<7} {stats['wins']:<5} {stats['losses']:<7} {win_pct:<7.1f} ${stats['pnl']:>9.2f}")

            print()
            print("BOTTOM 15 PERFORMERS:")
            print(f"{'Symbol':<10} {'Closed':<7} {'Wins':<5} {'Losses':<7} {'Win%':<7} {'P&L':>10}")
            print("-" * 60)
            for symbol, stats in sorted_symbols[-15:]:
                total = stats['trades']
                win_pct = (stats['wins'] / total * 100) if total > 0 else 0
                print(f"{symbol:<10} {total:<7} {stats['wins']:<5} {stats['losses']:<7} {win_pct:<7.1f} ${stats['pnl']:>9.2f}")

        print()
        print("=" * 80)

        # Show sample trades (first 10 closed positions)
        print()
        print("SAMPLE CLOSED TRADES:")
        print(f"{'Symbol':<10} {'Price':<12} {'Size':<12} {'Side':<6} {'P&L':>10}")
        print("-" * 60)

        closed_trades = [t for t in result['trades'] if t['realized_pnl'] is not None and t['realized_pnl'] != 0]
        for trade in closed_trades[:10]:
            side = 'SELL' if trade['is_ask'] else 'BUY'
            pnl = trade['realized_pnl']
            print(f"{trade['symbol']:<10} ${trade['price']:<11.4f} {trade['size']:<12.4f} {side:<6} ${pnl:>9.2f}")

        print()
        print("✅ Trade history fetched successfully from exchange API!")

    finally:
        await sdk.close()


if __name__ == '__main__':
    asyncio.run(test_trade_history())
