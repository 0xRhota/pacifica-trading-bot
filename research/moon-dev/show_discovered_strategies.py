#!/usr/bin/env python3
"""
Strategy Discovery Summary
Show discovered strategies when you return

Usage:
    python3 rbi_agent/show_discovered_strategies.py
"""

import json
import os
from datetime import datetime
from typing import List, Dict

PROVEN_STRATEGIES_FILE = "rbi_agent/proven_strategies.json"


def load_proven_strategies() -> List[Dict]:
    """Load proven strategies"""
    if not os.path.exists(PROVEN_STRATEGIES_FILE):
        return []
    
    try:
        with open(PROVEN_STRATEGIES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading strategies: {e}")
        return []


def show_strategies():
    """Display discovered strategies"""
    strategies = load_proven_strategies()
    
    print("=" * 80)
    print("DISCOVERED PROVEN STRATEGIES")
    print("=" * 80)
    
    if not strategies:
        print("\n⚠️  No proven strategies found yet")
        print("   Discovery may still be running, or no strategies passed thresholds")
        print(f"   Check logs: logs/rbi_auto_discovery.log")
        return
    
    print(f"\nTotal Proven Strategies: {len(strategies)}")
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Sort by return (descending)
    strategies.sort(key=lambda x: x.get('return_pct', 0), reverse=True)
    
    print("=" * 80)
    print("TOP STRATEGIES (by Return)")
    print("=" * 80)
    
    for i, strategy in enumerate(strategies[:10], 1):
        print(f"\n{i}. {strategy['strategy_name']}")
        print(f"   Description: {strategy['description']}")
        print(f"   ✅ Return: {strategy['return_pct']:.2f}%")
        print(f"   Win Rate: {strategy['win_rate']:.1%}")
        print(f"   Sharpe Ratio: {strategy['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown: {strategy['max_drawdown']:.2f}%")
        print(f"   Total Trades: {strategy['total_trades']}")
        
        if 'discovered_at' in strategy:
            print(f"   Discovered: {strategy['discovered_at']}")
        
        # Show results by symbol
        if 'results_by_symbol' in strategy and strategy['results_by_symbol']:
            print(f"   Results by Symbol:")
            for symbol, result in strategy['results_by_symbol'].items():
                print(f"     {symbol}: {result['return_pct']:.2f}% return, "
                      f"{result['win_rate']:.1%} win rate, "
                      f"{result['total_trades']} trades")
    
    if len(strategies) > 10:
        print(f"\n... and {len(strategies) - 10} more strategies")
    
    print("\n" + "=" * 80)
    print(f"📄 Full results: {PROVEN_STRATEGIES_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    show_strategies()


