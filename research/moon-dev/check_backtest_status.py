#!/usr/bin/env python3
"""
Monitor RBI Backtest Suite Progress
Shows current status and estimated completion time
"""

import os
import sys
import json
import subprocess
from datetime import datetime

def check_backtest_status():
    """Check if backtest suite is running"""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    running = "backtest_suite.py" in result.stdout
    return running

def get_latest_log():
    """Get latest log entries"""
    log_file = "logs/rbi_backtest.log"
    if not os.path.exists(log_file):
        return None
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
        return lines[-50:] if len(lines) > 50 else lines

def get_results():
    """Get results if available"""
    results_file = "rbi_agent/backtest_results.json"
    if not os.path.exists(results_file):
        return None
    
    with open(results_file, 'r') as f:
        return json.load(f)

def main():
    print("=" * 80)
    print("RBI BACKTEST SUITE STATUS")
    print("=" * 80)
    
    # Check if running
    is_running = check_backtest_status()
    
    if is_running:
        print("✅ Backtest suite is RUNNING")
        print("\nLatest log entries:")
        print("-" * 80)
        log_lines = get_latest_log()
        if log_lines:
            for line in log_lines[-10:]:
                print(line.rstrip())
        print("-" * 80)
        print("\n💡 Monitor progress: tail -f logs/rbi_backtest.log")
    else:
        print("❌ Backtest suite is NOT running")
    
    # Check for results
    results = get_results()
    if results:
        print("\n" + "=" * 80)
        print("RESULTS AVAILABLE")
        print("=" * 80)
        
        summary = results.get('summary', {})
        print(f"\nTotal Strategies: {summary.get('total_strategies', 0)}")
        print(f"Passed: {summary.get('passed', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        
        if summary.get('passed', 0) > 0:
            print(f"\nAverage Performance:")
            print(f"  Return: {summary.get('avg_return', 0):.2f}%")
            print(f"  Win Rate: {summary.get('avg_win_rate', 0):.1%}")
            print(f"  Sharpe Ratio: {summary.get('avg_sharpe', 0):.2f}")
        
        best = results.get('best_strategies', [])
        if best:
            print(f"\nTop 3 Strategies:")
            for i, strategy in enumerate(best[:3], 1):
                print(f"  {i}. {strategy.get('strategy_name', 'Unknown')}: "
                      f"{strategy.get('return_pct', 0):.2f}% return")
        
        print(f"\n📄 Full results: rbi_agent/backtest_results.json")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()


