#!/usr/bin/env python3
"""
Analyze Lighter trading performance using ACTUAL exchange data (CSV export)

Usage:
    python3 scripts/analyze_lighter_trades.py <csv_file>

Example:
    python3 scripts/analyze_lighter_trades.py lighter-trade-export-2025-11-08T18_44_46.435Z-UTC.csv
"""

import csv
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_trades(csv_file, hours=24):
    """Analyze trades from Lighter exchange CSV export"""

    # Read CSV
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        trades = list(reader)

    # Filter for time period
    now = datetime.now()
    cutoff = now - timedelta(hours=hours)

    recent_trades = []
    for trade in trades:
        date_str = trade['Date']
        trade_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        if trade_date >= cutoff:
            recent_trades.append(trade)

    # Calculate overall P&L
    total_pnl = 0
    wins = 0
    losses = 0
    win_pnl = 0
    loss_pnl = 0
    closed_count = 0

    for trade in recent_trades:
        if trade['Side'].startswith('Close'):
            pnl_str = trade['Closed PnL']
            if pnl_str and pnl_str != '-':
                pnl = float(pnl_str)
                total_pnl += pnl
                closed_count += 1

                if pnl > 0:
                    wins += 1
                    win_pnl += pnl
                else:
                    losses += 1
                    loss_pnl += pnl

    # Calculate per-symbol stats
    symbol_stats = defaultdict(lambda: {
        'pnl': 0,
        'wins': 0,
        'losses': 0,
        'trades': 0
    })

    for trade in recent_trades:
        if trade['Side'].startswith('Close'):
            market = trade['Market']
            pnl_str = trade['Closed PnL']

            if pnl_str and pnl_str != '-':
                pnl = float(pnl_str)
                symbol_stats[market]['pnl'] += pnl
                symbol_stats[market]['trades'] += 1

                if pnl > 0:
                    symbol_stats[market]['wins'] += 1
                else:
                    symbol_stats[market]['losses'] += 1

    # Print analysis
    print(f"=" * 80)
    print(f"LIGHTER TRADING ANALYSIS (Last {hours}h)")
    print(f"=" * 80)
    print(f"Data source: {csv_file}")
    print(f"Analysis time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Overall stats
    print(f"OVERALL PERFORMANCE:")
    print(f"  Total trades: {len(recent_trades)}")
    print(f"  Closed positions: {closed_count}")
    print(f"  Wins: {wins}")
    print(f"  Losses: {losses}")

    if wins + losses > 0:
        win_rate = (wins / (wins + losses)) * 100
        print(f"  Win Rate: {win_rate:.1f}%")

    print(f"  Total P&L: ${total_pnl:.2f}")
    print(f"  Winning P&L: ${win_pnl:.2f}")
    print(f"  Losing P&L: ${loss_pnl:.2f}")

    if wins > 0:
        avg_win = win_pnl / wins
        print(f"  Avg Win: ${avg_win:.2f}")

    if losses > 0:
        avg_loss = loss_pnl / losses
        print(f"  Avg Loss: ${avg_loss:.2f}")

    print()

    # Top performers
    sorted_symbols = sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)

    print(f"TOP 15 PERFORMERS:")
    print(f"{'Symbol':<10} {'Closed':<7} {'Wins':<5} {'Losses':<7} {'Win%':<7} {'P&L':>10}")
    print("-" * 60)
    for symbol, stats in sorted_symbols[:15]:
        total = stats['trades']
        win_pct = (stats['wins'] / total * 100) if total > 0 else 0
        print(f"{symbol:<10} {total:<7} {stats['wins']:<5} {stats['losses']:<7} {win_pct:<7.1f} ${stats['pnl']:>9.2f}")

    print()

    # Bottom performers
    print(f"BOTTOM 15 PERFORMERS:")
    print(f"{'Symbol':<10} {'Closed':<7} {'Wins':<5} {'Losses':<7} {'Win%':<7} {'P&L':>10}")
    print("-" * 60)
    for symbol, stats in sorted_symbols[-15:]:
        total = stats['trades']
        win_pct = (stats['wins'] / total * 100) if total > 0 else 0
        print(f"{symbol:<10} {total:<7} {stats['wins']:<5} {stats['losses']:<7} {win_pct:<7.1f} ${stats['pnl']:>9.2f}")

    print()
    print("=" * 80)

    # Return data for programmatic use
    return {
        'total_pnl': total_pnl,
        'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
        'wins': wins,
        'losses': losses,
        'symbol_stats': dict(symbol_stats)
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/analyze_lighter_trades.py <csv_file>")
        print("Example: python3 scripts/analyze_lighter_trades.py lighter-trade-export.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Run analysis
    analyze_trades(csv_file, hours=24)
