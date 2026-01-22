#!/usr/bin/env python3
"""
Hibachi Performance Dashboard
Shows real-time performance of both Grid MM and LLM bots

HIB-007 (2026-01-22): Performance visibility for trading operations

Usage:
    python3 scripts/hibachi_dashboard.py
    python3 scripts/hibachi_dashboard.py --watch  # Auto-refresh every 30s
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Dict, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key] = val.strip('"').strip("'")

from dexes.hibachi.hibachi_sdk import HibachiSDK
from trade_tracker import TradeTracker


class HibachiDashboard:
    """Performance dashboard for Hibachi trading operations."""

    def __init__(self):
        """Initialize dashboard."""
        api_key = os.getenv('HIBACHI_PUBLIC_KEY')
        api_secret = os.getenv('HIBACHI_PRIVATE_KEY')
        account_id = os.getenv('HIBACHI_ACCOUNT_ID')

        if not api_key or not api_secret or not account_id:
            raise ValueError("HIBACHI_PUBLIC_KEY, HIBACHI_PRIVATE_KEY, HIBACHI_ACCOUNT_ID required")

        self.sdk = HibachiSDK(api_key, api_secret, account_id)
        self.tracker = TradeTracker(dex="hibachi")

    async def get_account_info(self) -> Dict:
        """Get account balance and positions."""
        balance = await self.sdk.get_balance() or 0
        positions = await self.sdk.get_positions()
        return {
            'balance': balance,
            'positions': positions or []
        }

    def get_llm_stats(self, hours: int = 24) -> Dict:
        """Get LLM bot trading statistics."""
        cutoff = datetime.now() - timedelta(hours=hours)
        trades = [t for t in self.tracker.trades if t.get('status') == 'closed']

        # Filter by time
        recent_trades = []
        for t in trades:
            try:
                exit_time = datetime.fromisoformat(t.get('exit_timestamp', ''))
                if exit_time >= cutoff:
                    recent_trades.append(t)
            except (ValueError, TypeError):
                continue

        # Calculate stats
        total = len(recent_trades)
        wins = len([t for t in recent_trades if (t.get('pnl') or 0) > 0])
        total_pnl = sum((t.get('pnl') or 0) for t in recent_trades)
        win_rate = wins / total if total > 0 else 0

        # By symbol
        by_symbol = {}
        for t in recent_trades:
            symbol = t.get('symbol', 'UNKNOWN')
            if symbol not in by_symbol:
                by_symbol[symbol] = {'wins': 0, 'losses': 0, 'pnl': 0}
            if (t.get('pnl') or 0) > 0:
                by_symbol[symbol]['wins'] += 1
            else:
                by_symbol[symbol]['losses'] += 1
            by_symbol[symbol]['pnl'] += t.get('pnl') or 0

        return {
            'total_trades': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'by_symbol': by_symbol
        }

    def get_grid_mm_stats(self) -> Dict:
        """Get Grid MM stats from log file."""
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'grid_mm_hibachi.log')

        stats = {
            'cycles': 0,
            'runtime_min': 0,
            'fills': 0,
            'pnl': 0,
            'last_update': None
        }

        if not os.path.exists(log_path):
            return stats

        try:
            # Read last 100 lines for stats
            with open(log_path, 'r') as f:
                lines = f.readlines()[-100:]

            for line in reversed(lines):
                if 'Stats:' in line:
                    # Parse: Stats: 360 cycles in 218.7 min | Balance: $47.22 | PnL: $-2.80
                    parts = line.split('|')
                    for part in parts:
                        if 'cycles' in part:
                            try:
                                stats['cycles'] = int(part.split()[1])
                                stats['runtime_min'] = float(part.split()[4])
                            except (ValueError, IndexError):
                                pass
                        elif 'PnL' in part:
                            try:
                                pnl_str = part.split('$')[1].strip()
                                stats['pnl'] = float(pnl_str)
                            except (ValueError, IndexError):
                                pass
                    stats['last_update'] = line.split('|')[0].strip()
                    break

        except Exception as e:
            print(f"Error reading Grid MM log: {e}")

        return stats

    async def display(self):
        """Display the dashboard."""
        print("\n" + "=" * 70)
        print("📊 HIBACHI PERFORMANCE DASHBOARD")
        print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Account Info
        print("\n┌─────────────────────────────────────────────────────────────────┐")
        print("│ 💰 ACCOUNT SUMMARY                                              │")
        print("├─────────────────────────────────────────────────────────────────┤")

        try:
            account = await self.get_account_info()
            print(f"│ Balance:          ${account['balance']:.2f}")
            print(f"│ Open Positions:   {len(account['positions'])}")

            if account['positions']:
                print("│")
                for pos in account['positions']:
                    symbol = pos.get('symbol', 'UNKNOWN')
                    qty = float(pos.get('quantity', 0))
                    direction = pos.get('direction', 'Unknown')
                    if qty != 0:
                        print(f"│   {symbol}: {direction} {qty:.4f}")
        except Exception as e:
            print(f"│ Error fetching account: {e}")

        print("└─────────────────────────────────────────────────────────────────┘")

        # LLM Bot Stats (24h)
        print("\n┌─────────────────────────────────────────────────────────────────┐")
        print("│ 🤖 LLM DIRECTIONAL BOT (24h)                                    │")
        print("├─────────────────────────────────────────────────────────────────┤")

        llm_stats = self.get_llm_stats(hours=24)
        print(f"│ Trades:      {llm_stats['total_trades']}")
        print(f"│ Wins/Losses: {llm_stats['wins']}/{llm_stats['losses']}")
        print(f"│ Win Rate:    {llm_stats['win_rate']:.1%}")
        print(f"│ Total P&L:   ${llm_stats['total_pnl']:+.2f}")

        if llm_stats['by_symbol']:
            print("│")
            print("│ By Symbol:")
            for symbol, data in llm_stats['by_symbol'].items():
                total = data['wins'] + data['losses']
                wr = data['wins'] / total if total > 0 else 0
                status = "✅" if wr >= 0.5 else "⚠️" if wr >= 0.3 else "❌"
                print(f"│   {symbol}: {wr:.0%} WR ({data['wins']}/{total}), ${data['pnl']:+.2f} {status}")

        print("└─────────────────────────────────────────────────────────────────┘")

        # Grid MM Stats
        print("\n┌─────────────────────────────────────────────────────────────────┐")
        print("│ 📈 GRID MARKET MAKER (BTC)                                      │")
        print("├─────────────────────────────────────────────────────────────────┤")

        grid_stats = self.get_grid_mm_stats()
        print(f"│ Cycles:      {grid_stats['cycles']}")
        print(f"│ Runtime:     {grid_stats['runtime_min']:.1f} min")
        print(f"│ P&L:         ${grid_stats['pnl']:+.2f}")
        if grid_stats['last_update']:
            print(f"│ Last Update: {grid_stats['last_update']}")

        print("└─────────────────────────────────────────────────────────────────┘")

        # Combined Summary
        combined_pnl = llm_stats['total_pnl'] + grid_stats['pnl']
        print("\n┌─────────────────────────────────────────────────────────────────┐")
        print("│ 📊 COMBINED DAILY PERFORMANCE                                   │")
        print("├─────────────────────────────────────────────────────────────────┤")
        status_emoji = "🟢" if combined_pnl > 0 else "🔴"
        print(f"│ LLM Bot P&L:   ${llm_stats['total_pnl']:+.2f}")
        print(f"│ Grid MM P&L:   ${grid_stats['pnl']:+.2f}")
        print(f"│ Combined:      ${combined_pnl:+.2f} {status_emoji}")
        print("└─────────────────────────────────────────────────────────────────┘")

        print("\n" + "=" * 70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Hibachi Performance Dashboard")
    parser.add_argument('--watch', action='store_true', help='Auto-refresh every 30s')
    args = parser.parse_args()

    dashboard = HibachiDashboard()

    if args.watch:
        print("Dashboard running in watch mode (Ctrl+C to stop)")
        while True:
            try:
                # Clear screen
                os.system('clear' if os.name != 'nt' else 'cls')
                await dashboard.display()
                print("\nRefreshing in 30 seconds... (Ctrl+C to stop)")
                await asyncio.sleep(30)
            except KeyboardInterrupt:
                print("\nDashboard stopped.")
                break
    else:
        await dashboard.display()


if __name__ == "__main__":
    asyncio.run(main())
