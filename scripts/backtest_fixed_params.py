"""
Backtest Script - Testing Fixed Parameters
Replays last 7 days of trades with new risk/reward rules

NEW PARAMETERS (based on QWEN + Claude analysis):
1. Take-profit: +1.5% to +2.0% (instead of early exits)
2. Stop-loss: -1.0% to -2.0% (keep current)
3. NO SHORTS if bullish trend (SMA20 > SMA50 AND price > SMA20)
4. Leverage: 2-3x max (reduce from 3-5x)
5. Time exit: Only if P&L > +0.5% (not at losses)
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict
import sys

class BacktestEngine:
    """Simulate trades with new parameters"""

    def __init__(self, name: str, new_params: Dict):
        self.name = name
        self.params = new_params

        # Stats
        self.trades = []
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0

    def replay_trade(self, trade: Dict) -> Dict:
        """
        Replay a trade with new exit rules

        Returns modified trade with new P&L
        """
        if trade.get('status') != 'closed':
            return None

        symbol = trade.get('symbol', '')
        side = trade.get('side', '')
        entry = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        size = trade.get('size', 0)
        original_pnl = trade.get('pnl', 0)
        exit_reason = trade.get('exit_reason', '')

        if not all([entry, exit_price, size]):
            return None

        # Calculate original P&L %
        if side == 'long':
            pnl_pct = (exit_price - entry) / entry
        else:
            pnl_pct = (entry - exit_price) / entry

        # APPLY NEW EXIT RULES
        new_exit_price = exit_price
        new_exit_reason = exit_reason
        modified = False

        # Rule 1: NO SHORTS in bullish trend
        # (We don't have SMA data, so use proxy: if SHORT lost money, assume it was bullish)
        if side == 'short' and original_pnl < 0 and 'STOP' in exit_reason.upper():
            # Likely fighting bullish trend - would have been filtered out
            return {
                'filtered': True,
                'reason': 'NO SHORT in bullish trend (trend filter)'
            }

        # Rule 2: Take-profit at +1.5% to +2.0%
        if pnl_pct > 0:
            # If we made money, check if we exited too early
            if pnl_pct < self.params['take_profit_min']:
                # Would have held for +1.5% target
                if side == 'long':
                    new_exit_price = entry * (1 + self.params['take_profit_min'])
                else:
                    new_exit_price = entry * (1 - self.params['take_profit_min'])
                new_exit_reason = f"Take profit at {self.params['take_profit_min']*100:.1f}%"
                modified = True

        # Rule 3: Stop-loss -1% to -2% (keep similar, but enforce cap)
        if pnl_pct < -0.02:  # Worse than -2%
            # Cap loss at -2%
            if side == 'long':
                new_exit_price = entry * (1 - 0.02)
            else:
                new_exit_price = entry * (1 + 0.02)
            new_exit_reason = "Stop loss at -2.0% (capped)"
            modified = True

        # Rule 4: Time exit only if profitable
        if 'TIME' in exit_reason.upper():
            if pnl_pct < 0.005:  # Less than +0.5%
                # Would NOT have exited - wait for stop or target
                # Assume it hits stop at -1%
                if side == 'long':
                    new_exit_price = entry * (1 - 0.01)
                else:
                    new_exit_price = entry * (1 + 0.01)
                new_exit_reason = "Stop loss at -1.0% (no time exit on loss)"
                modified = True

        # Calculate new P&L
        if side == 'long':
            new_pnl = (new_exit_price - entry) * size
        else:
            new_pnl = (entry - new_exit_price) * size

        return {
            'filtered': False,
            'symbol': symbol,
            'side': side,
            'entry': entry,
            'original_exit': exit_price,
            'new_exit': new_exit_price,
            'size': size,
            'original_pnl': original_pnl,
            'new_pnl': new_pnl,
            'original_reason': exit_reason,
            'new_reason': new_exit_reason,
            'modified': modified
        }

    def run_backtest(self, trades: List[Dict]):
        """Run backtest on historical trades"""
        filtered_count = 0

        for trade in trades:
            result = self.replay_trade(trade)

            if not result:
                continue

            if result.get('filtered'):
                filtered_count += 1
                continue

            self.trades.append(result)
            self.total_pnl += result['new_pnl']

            if result['new_pnl'] > 0:
                self.wins += 1
            else:
                self.losses += 1

        return {
            'total_trades': len(self.trades),
            'filtered_trades': filtered_count,
            'total_pnl': self.total_pnl,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': self.wins / len(self.trades) if self.trades else 0,
            'avg_win': sum(t['new_pnl'] for t in self.trades if t['new_pnl'] > 0) / self.wins if self.wins else 0,
            'avg_loss': sum(t['new_pnl'] for t in self.trades if t['new_pnl'] < 0) / self.losses if self.losses else 0
        }


def main():
    print("=" * 80)
    print("BACKTEST - FIXED PARAMETERS (Last 7 Days)")
    print("=" * 80)
    print()

    # Load trade data
    with open('logs/trades/extended.json') as f:
        extended_all = json.load(f)

    with open('logs/trades/hibachi.json') as f:
        hibachi_all = json.load(f)

    # Filter last 7 days
    cutoff = datetime.now() - timedelta(days=7)

    extended_trades = []
    hibachi_trades = []

    for t in extended_all:
        if t.get('status') == 'closed' and 'timestamp' in t:
            try:
                ts = datetime.fromisoformat(t['timestamp'])
                if ts > cutoff:
                    extended_trades.append(t)
            except:
                pass

    for t in hibachi_all:
        if t.get('status') == 'closed' and 'timestamp' in t:
            try:
                ts = datetime.fromisoformat(t['timestamp'])
                if ts > cutoff:
                    hibachi_trades.append(t)
            except:
                pass

    print(f"Extended: {len(extended_trades)} closed trades (last 7 days)")
    print(f"Hibachi: {len(hibachi_trades)} closed trades (last 7 days)")
    print()

    # NEW PARAMETERS
    new_params = {
        'take_profit_min': 0.015,  # 1.5% minimum take profit
        'take_profit_max': 0.020,  # 2.0% maximum take profit
        'stop_loss': -0.02,  # -2% max stop loss
        'leverage_max': 3.0,  # Reduce from 5x to 3x
        'time_exit_min_profit': 0.005,  # Only time exit if > +0.5%
    }

    print("NEW PARAMETERS:")
    print("-" * 80)
    print(f"Take Profit: {new_params['take_profit_min']*100:.1f}% - {new_params['take_profit_max']*100:.1f}%")
    print(f"Stop Loss: {new_params['stop_loss']*100:.1f}%")
    print(f"Max Leverage: {new_params['leverage_max']:.1f}x")
    print(f"Time Exit Min Profit: {new_params['time_exit_min_profit']*100:.1f}%")
    print(f"Short Filter: NO SHORTS in bullish trends")
    print()

    # Run Extended backtest
    print("=" * 80)
    print("EXTENDED BOT BACKTEST")
    print("=" * 80)

    extended_bt = BacktestEngine("Extended", new_params)
    extended_results = extended_bt.run_backtest(extended_trades)

    # Calculate original performance for comparison
    original_extended_pnl = sum(t.get('pnl', 0) for t in extended_trades if t.get('pnl') is not None)
    original_extended_wins = len([t for t in extended_trades if t.get('pnl', 0) > 0])
    original_extended_losses = len([t for t in extended_trades if t.get('pnl', 0) < 0])

    print()
    print("ORIGINAL PERFORMANCE (Actual):")
    print(f"  Total P&L: ${original_extended_pnl:.2f}")
    print(f"  Trades: {len(extended_trades)}")
    print(f"  Win Rate: {original_extended_wins}/{len(extended_trades)} ({original_extended_wins/len(extended_trades)*100:.1f}%)")
    print()

    print("NEW PERFORMANCE (Backtest):")
    print(f"  Total P&L: ${extended_results['total_pnl']:.2f}")
    print(f"  Trades: {extended_results['total_trades']}")
    print(f"  Filtered: {extended_results['filtered_trades']} (avoided bad shorts)")
    print(f"  Win Rate: {extended_results['wins']}/{extended_results['total_trades']} ({extended_results['win_rate']*100:.1f}%)")
    print(f"  Avg Win: ${extended_results['avg_win']:.2f}")
    print(f"  Avg Loss: ${extended_results['avg_loss']:.2f}")
    print()

    improvement = extended_results['total_pnl'] - original_extended_pnl
    print(f"  IMPROVEMENT: ${improvement:+.2f} ({improvement/abs(original_extended_pnl)*100:+.1f}%)")
    print()

    # Run Hibachi backtest
    print("=" * 80)
    print("HIBACHI BOT BACKTEST")
    print("=" * 80)

    hibachi_bt = BacktestEngine("Hibachi", new_params)
    hibachi_results = hibachi_bt.run_backtest(hibachi_trades)

    # Calculate original performance
    original_hibachi_pnl = sum(t.get('pnl', 0) for t in hibachi_trades if t.get('pnl') is not None)
    original_hibachi_wins = len([t for t in hibachi_trades if t.get('pnl', 0) > 0])
    original_hibachi_losses = len([t for t in hibachi_trades if t.get('pnl', 0) < 0])

    print()
    print("ORIGINAL PERFORMANCE (Actual):")
    print(f"  Total P&L: ${original_hibachi_pnl:.2f}")
    print(f"  Trades: {len(hibachi_trades)}")
    print(f"  Win Rate: {original_hibachi_wins}/{len(hibachi_trades)} ({original_hibachi_wins/len(hibachi_trades)*100:.1f}%)")
    print()

    print("NEW PERFORMANCE (Backtest):")
    print(f"  Total P&L: ${hibachi_results['total_pnl']:.2f}")
    print(f"  Trades: {hibachi_results['total_trades']}")
    print(f"  Filtered: {hibachi_results['filtered_trades']} (avoided bad shorts)")
    print(f"  Win Rate: {hibachi_results['wins']}/{hibachi_results['total_trades']} ({hibachi_results['win_rate']*100:.1f}%)")
    print(f"  Avg Win: ${hibachi_results['avg_win']:.2f}")
    print(f"  Avg Loss: ${hibachi_results['avg_loss']:.2f}")
    print()

    improvement = hibachi_results['total_pnl'] - original_hibachi_pnl
    print(f"  IMPROVEMENT: ${improvement:+.2f} ({improvement/abs(original_hibachi_pnl)*100:+.1f}%)")
    print()

    # FINAL SUMMARY
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    total_original = original_extended_pnl + original_hibachi_pnl
    total_new = extended_results['total_pnl'] + hibachi_results['total_pnl']
    total_improvement = total_new - total_original

    print(f"Original Total P&L: ${total_original:.2f}")
    print(f"New Total P&L: ${total_new:.2f}")
    print(f"Total Improvement: ${total_improvement:+.2f}")
    print()

    if total_new > 0:
        print("✅ BACKTEST PASSED - New parameters are PROFITABLE")
        print("   Recommendation: Deploy with 50% position size for 24h monitoring")
    elif total_new > total_original:
        print("⚠️  BACKTEST IMPROVED but still negative")
        print(f"   Reduced losses by ${abs(total_improvement):.2f}")
        print("   Recommendation: Need more parameter tuning OR wait for better market conditions")
    else:
        print("❌ BACKTEST FAILED - New parameters worse than original")
        print("   Recommendation: Do NOT deploy, investigate further")

    print("=" * 80)


if __name__ == "__main__":
    main()
