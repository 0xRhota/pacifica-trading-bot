"""
Trade Tracking System - DEX-aware with automatic rotation
Maintains separate logs per DEX with size limits
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class TradeEntry:
    """Individual trade entry"""
    timestamp: str
    dex: str  # "pacifica" or "lighter"
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
    confidence: Optional[float] = None  # Track LLM confidence at entry

class TradeTracker:
    """DEX-aware trade tracker with automatic rotation"""

    MAX_TRADES_PER_FILE = 1000  # Rotate after 1000 trades

    def __init__(self, dex: str, log_dir: str = "logs/trades"):
        """
        Initialize tracker for specific DEX

        Args:
            dex: "pacifica" or "lighter"
            log_dir: Directory for trade logs
        """
        self.dex = dex.lower()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{self.dex}.json"
        self.trades: List[Dict] = []
        self._load_trades()

    def _load_trades(self):
        """Load existing trades from file"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    self.trades = json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load {self.log_file}, starting fresh")
                self.trades = []
        else:
            self.trades = []

    def _save_trades(self):
        """Save trades to file with rotation if needed"""
        # Rotate if too large
        if len(self.trades) > self.MAX_TRADES_PER_FILE:
            self._rotate_log()

        with open(self.log_file, 'w') as f:
            json.dump(self.trades, f, indent=2)

    def _rotate_log(self):
        """Rotate log file when it gets too large"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = self.log_dir / f"{self.dex}_{timestamp}.json"

        # Move current file to archive
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                old_trades = json.load(f)

            with open(archive_file, 'w') as f:
                json.dump(old_trades, f, indent=2)

        # Keep only last 100 trades in active file
        self.trades = self.trades[-100:]
        print(f"📦 Rotated {self.dex} trade log to {archive_file}")

    def log_entry(self, order_id: Optional[str], symbol: str, side: str,
                  size: float, entry_price: float, notes: str = None,
                  confidence: float = None) -> str:
        """
        Log a new trade entry

        Returns:
            trade_id: Unique identifier for this trade
        """
        timestamp = datetime.now().isoformat()
        trade_id = f"{self.dex}_{symbol}_{timestamp}_{order_id or 'manual'}"

        trade = TradeEntry(
            timestamp=timestamp,
            dex=self.dex,
            order_id=order_id,
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            status="open",
            notes=notes,
            confidence=confidence
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
                trade['pnl'] = round(pnl - fees, 4)
                trade['pnl_pct'] = round(pnl_pct, 4)
                trade['fees'] = fees
                trade['exit_reason'] = exit_reason
                trade['status'] = 'closed'

                self._save_trades()
                return

        print(f"Warning: Could not find open trade with order_id {order_id}")
    
    def get_order_id_for_symbol(self, symbol: str) -> Optional[str]:
        """Get order_id for the most recent open trade for symbol"""
        # Search in reverse order (most recent first)
        for trade in reversed(self.trades):
            if trade.get('symbol') == symbol and trade.get('status') == 'open':
                return trade.get('order_id')
        return None
    
    def get_open_trade_for_symbol(self, symbol: str) -> Optional[Dict]:
        """Get the most recent open trade for symbol"""
        for trade in reversed(self.trades):
            if trade.get('symbol') == symbol and trade.get('status') == 'open':
                return trade
        return None

    def get_open_trades(self) -> List[Dict]:
        return [t for t in self.trades if t['status'] == 'open']

    def get_closed_trades(self) -> List[Dict]:
        return [t for t in self.trades if t['status'] == 'closed']

    def get_recent_trades(self, hours: int = 24, limit: int = 20) -> List[Dict]:
        """
        Get recent trades within specified hours
        
        Args:
            hours: Hours to look back (default: 24)
            limit: Max trades to return (default: 20)
            
        Returns:
            List of recent trades sorted by timestamp (newest first)
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for trade in reversed(self.trades):  # Start from newest
            trade_time = datetime.fromisoformat(trade['timestamp'])
            if trade_time >= cutoff:
                recent.append(trade)
                if len(recent) >= limit:
                    break
        
        return recent

    def get_recently_closed_symbols(self, hours: int = 2) -> List[str]:
        """
        Get symbols that were recently closed (within last N hours)
        Useful for preventing immediate re-entry
        
        Args:
            hours: Hours to look back (default: 2)
            
        Returns:
            List of symbols that were recently closed
        """
        recent_closed = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        for trade in reversed(self.trades):
            if trade['status'] == 'closed' and trade.get('exit_timestamp'):
                exit_time = datetime.fromisoformat(trade['exit_timestamp'])
                if exit_time >= cutoff:
                    if trade['symbol'] not in recent_closed:
                        recent_closed.append(trade['symbol'])
        
        return recent_closed

    def get_stats(self) -> Dict:
        """Calculate trading statistics"""
        closed = self.get_closed_trades()
        if not closed:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "avg_fees": 0.0
            }

        wins = [t for t in closed if t.get('pnl', 0) > 0]
        losses = [t for t in closed if t.get('pnl', 0) <= 0]

        total_pnl = sum(t.get('pnl', 0) for t in closed)
        total_fees = sum(t.get('fees', 0) for t in closed)

        return {
            "dex": self.dex,
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed) if closed else 0.0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(closed), 2) if closed else 0.0,
            "total_fees": round(total_fees, 2),
            "avg_fees": round(total_fees / len(closed), 2) if closed else 0.0,
            "open_positions": len(self.get_open_trades())
        }

    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print(f"📊 TRADING STATS - {stats['dex'].upper()}")
        print("=" * 60)
        print(f"Total Trades:    {stats['total_trades']}")
        print(f"Wins/Losses:     {stats['wins']}/{stats['losses']}")
        print(f"Win Rate:        {stats['win_rate']:.1%}")
        print(f"Total P&L:       ${stats['total_pnl']:.2f}")
        print(f"Avg P&L/Trade:   ${stats['avg_pnl']:.2f}")
        print(f"Total Fees:      ${stats['total_fees']:.2f}")
        print(f"Open Positions:  {stats['open_positions']}")
        print("=" * 60 + "\n")


# Create global instances for each DEX
pacifica_tracker = TradeTracker("pacifica")
lighter_tracker = TradeTracker("lighter")

# Backwards compatibility - defaults to Pacifica
tracker = pacifica_tracker
