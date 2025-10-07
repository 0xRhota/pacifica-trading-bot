#!/usr/bin/env python3
"""
View trading statistics and history
"""

from trade_tracker import TradeTracker

def main():
    tracker = TradeTracker("trades.json")

    # Print stats
    tracker.print_stats()

    # Show recent trades
    closed = tracker.get_closed_trades()
    open_trades = tracker.get_open_trades()

    if open_trades:
        print("\n" + "="*60)
        print("OPEN POSITIONS")
        print("="*60)
        for trade in open_trades:
            print(f"{trade['symbol']} {trade['side'].upper()}: {trade['size']:.6f} @ ${trade['entry_price']:.2f}")
            print(f"  Opened: {trade['timestamp']}")
            print(f"  Order ID: {trade.get('order_id', 'N/A')}")
            if trade.get('notes'):
                print(f"  Notes: {trade['notes']}")
            print()

    if closed:
        print("="*60)
        print("RECENT CLOSED TRADES (Last 10)")
        print("="*60)
        for trade in closed[-10:]:
            pnl_symbol = "✅" if trade.get('pnl', 0) > 0 else "❌"
            print(f"{pnl_symbol} {trade['symbol']} {trade['side'].upper()}: ${trade.get('pnl', 0):.4f} ({trade.get('pnl_pct', 0):.2%})")
            print(f"   Entry: ${trade['entry_price']:.2f} → Exit: ${trade.get('exit_price', 0):.2f}")
            print(f"   Reason: {trade.get('exit_reason', 'N/A')}")
            print()

if __name__ == "__main__":
    main()
