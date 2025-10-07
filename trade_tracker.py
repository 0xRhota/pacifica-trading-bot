"""
Trade tracking system - logs all entries, exits, and results
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class TradeEntry:
    """Individual trade entry"""
    timestamp: str
    order_id: Optional[str]
    symbol: str
    side: str  # "buy" or "sell"
    size: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    fees: Optional[float] = None
    exit_timestamp: Optional[str] = None
    exit_reason: Optional[str] = None
    status: str = "open"  # "open", "closed", "failed"
    notes: Optional[str] = None

class TradeTracker:
    """Track all trades and generate analytics"""

    def __init__(self, log_file: str = "trades.json"):
        self.log_file = log_file
        self.trades: List[Dict] = []
        self._load_trades()

    def _load_trades(self):
        """Load existing trades from file"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    self.trades = json.load(f)
            except:
                self.trades = []
        else:
            self.trades = []

    def _save_trades(self):
        """Save trades to file"""
        with open(self.log_file, 'w') as f:
            json.dump(self.trades, f, indent=2)

    def log_entry(self, order_id: Optional[str], symbol: str, side: str,
                  size: float, entry_price: float, notes: str = None) -> str:
        """
        Log a new trade entry

        Returns:
            trade_id: Unique identifier for this trade
        """
        timestamp = datetime.now().isoformat()
        trade_id = f"{symbol}_{timestamp}_{order_id or 'manual'}"

        trade = TradeEntry(
            timestamp=timestamp,
            order_id=order_id,
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            status="open",
            notes=notes
        )

        self.trades.append(asdict(trade))
        self._save_trades()

        return trade_id

    def log_exit(self, order_id: str, exit_price: float, exit_reason: str = None,
                 fees: float = 0.0):
        """Log trade exit and calculate P&L"""
        # Find the trade by order_id
        for trade in reversed(self.trades):
            if trade.get('order_id') == order_id and trade['status'] == 'open':
                # Calculate P&L
                entry_price = trade['entry_price']
                size = trade['size']
                side = trade['side']

                if side == "buy":
                    pnl = (exit_price - entry_price) * size
                    pnl_pct = (exit_price - entry_price) / entry_price
                else:  # sell/short
                    pnl = (entry_price - exit_price) * size
                    pnl_pct = (entry_price - exit_price) / entry_price

                # Update trade
                trade['exit_price'] = exit_price
                trade['exit_timestamp'] = datetime.now().isoformat()
                trade['exit_reason'] = exit_reason
                trade['pnl'] = pnl - fees
                trade['pnl_pct'] = pnl_pct
                trade['fees'] = fees
                trade['status'] = 'closed'

                self._save_trades()
                return True

        return False

    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        return [t for t in self.trades if t['status'] == 'open']

    def get_closed_trades(self) -> List[Dict]:
        """Get all closed trades"""
        return [t for t in self.trades if t['status'] == 'closed']

    def get_stats(self) -> Dict:
        """Calculate trading statistics"""
        closed = self.get_closed_trades()

        if not closed:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'total_fees': 0,
                'best_trade': None,
                'worst_trade': None
            }

        winning_trades = [t for t in closed if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed if t.get('pnl', 0) <= 0]

        total_pnl = sum(t.get('pnl', 0) for t in closed)
        total_fees = sum(t.get('fees', 0) for t in closed)

        best_trade = max(closed, key=lambda x: x.get('pnl', 0))
        worst_trade = min(closed, key=lambda x: x.get('pnl', 0))

        return {
            'total_trades': len(closed),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(closed) if closed else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(closed) if closed else 0,
            'total_fees': total_fees,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_win': sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        }

    def print_stats(self):
        """Print trading statistics"""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("TRADING STATISTICS")
        print("="*60)
        print(f"Total Trades:      {stats['total_trades']}")

        if stats['total_trades'] > 0:
            print(f"Winning Trades:    {stats['winning_trades']}")
            print(f"Losing Trades:     {stats['losing_trades']}")
            print(f"Win Rate:          {stats['win_rate']:.2%}")
            print(f"Total P&L:         ${stats['total_pnl']:.4f}")
            print(f"Average P&L:       ${stats['avg_pnl']:.4f}")
            print(f"Total Fees:        ${stats['total_fees']:.4f}")

        if stats.get('best_trade'):
            print(f"\nBest Trade:        ${stats['best_trade']['pnl']:.4f} ({stats['best_trade']['symbol']})")
        if stats.get('worst_trade'):
            print(f"Worst Trade:       ${stats['worst_trade']['pnl']:.4f} ({stats['worst_trade']['symbol']})")

        if stats.get('avg_win', 0) > 0:
            print(f"\nAverage Win:       ${stats['avg_win']:.4f}")
        if stats.get('avg_loss', 0) < 0:
            print(f"Average Loss:      ${stats['avg_loss']:.4f}")

        print("="*60)

    def export_csv(self, filename: str = "trades.csv"):
        """Export trades to CSV"""
        import csv

        if not self.trades:
            print("No trades to export")
            return

        keys = self.trades[0].keys()
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.trades)

        print(f"Exported {len(self.trades)} trades to {filename}")


# Global tracker instance
tracker = TradeTracker()
