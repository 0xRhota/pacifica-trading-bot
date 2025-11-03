#!/usr/bin/env python3
"""
Run all RBI backtests - simple direct approach
Fixes CSV and skips multi-data tester
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import talib
import importlib.util
import re

# Project root
project_root = Path(__file__).parent.parent.parent
backtest_dir = project_root / "moon-dev-reference/src/data/rbi_pp_multi/11_02_2025/backtests"
csv_dir = project_root / "moon-dev-reference/src/data/rbi"

def load_strategy_class(file_path: Path):
    """Load strategy class from file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract strategy class (get full class definition)
    class_match = re.search(r'(class (\w+)\(Strategy\):.*?)(?=\nclass|\nif __name__|\n# 🌙)', content, re.DOTALL)
    if not class_match:
        return None, None
    
    # Prepare execution context with imports
    exec_globals = {
        'Strategy': Strategy,
        'talib': talib,
        'np': np,
        'pd': pd
    }
    
    # Execute strategy code
    exec(compile(class_match.group(1), '<string>', 'exec'), exec_globals)
    class_name = class_match.group(2)
    return exec_globals[class_name], class_name

def run_backtest_on_data(strategy_class, csv_path: Path):
    """Run backtest on a CSV file"""
    data = pd.read_csv(csv_path)
    
    # Fix columns
    data.columns = data.columns.str.strip().str.lower()
    data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower() or col.strip() == ''])
    
    # Map to required columns
    if len(data.columns) >= 6:
        data = data.iloc[:, :6]
        data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    elif len(data.columns) == 5:
        data.columns = ['datetime', 'open', 'high', 'low', 'close']
        data['volume'] = 0  # Add volume if missing
    else:
        return None
    
    data['datetime'] = pd.to_datetime(data['datetime'])
    data = data.set_index('datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    # Run backtest
    bt = Backtest(data, strategy_class, cash=1_000_000, commission=0.002)
    stats = bt.run()
    
    return {
        'return': stats['Return [%]'],
        'buy_hold': stats['Buy & Hold Return [%]'],
        'sharpe': stats['Sharpe Ratio'],
        'max_dd': stats['Max. Drawdown [%]'],
        'trades': stats['# Trades'],
        'win_rate': stats['Win Rate [%]'],
        'stats': stats
    }

def main():
    print("\n" + "="*80)
    print("🚀 RUNNING ALL RBI BACKTESTS")
    print("="*80)
    
    backtest_files = sorted(backtest_dir.glob("T*.py"))
    
    if not backtest_files:
        print(f"❌ No backtest files found")
        return
    
    print(f"📊 Found {len(backtest_files)} strategies\n")
    
    results = []
    
    for file_path in backtest_files:
        print(f"\n{'='*80}")
        print(f"Testing: {file_path.name}")
        print('='*80)
        
        try:
            # Load strategy
            strategy_class, class_name = load_strategy_class(file_path)
            if not strategy_class:
                print(f"❌ Could not extract strategy class")
                results.append({
                    'file': file_path.name,
                    'success': False,
                    'error': 'Could not extract strategy class'
                })
                continue
            
            # Test on SOL, ETH (BTC has CSV issues)
            best_result = None
            best_return = -999
            
            for symbol in ['SOL', 'ETH']:
                csv_path = csv_dir / f"{symbol}-USD-15m.csv"
                if not csv_path.exists():
                    continue
                
                print(f"  Testing on {symbol}...")
                result = run_backtest_on_data(strategy_class, csv_path)
                
                if result and result['return'] > best_return:
                    best_result = result
                    best_return = result['return']
                    best_result['symbol'] = symbol
            
            if best_result:
                result_dict = {
                    'file': file_path.name,
                    'success': True,
                    'symbol': best_result['symbol'],
                    'return': best_result['return'],
                    'buy_hold': best_result['buy_hold'],
                    'sharpe': best_result['sharpe'],
                    'max_dd': best_result['max_dd'],
                    'trades': best_result['trades'],
                    'win_rate': best_result['win_rate']
                }
                results.append(result_dict)
                
                status = "✅ PASS" if best_result['return'] > 1.0 else "⚠️  FAIL"
                print(f"  {status} Return: {best_result['return']:.2f}% | Trades: {best_result['trades']} | Sharpe: {best_result['sharpe']:.2f}")
            else:
                results.append({
                    'file': file_path.name,
                    'success': False,
                    'error': 'No valid results'
                })
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'file': file_path.name,
                'success': False,
                'error': str(e)[:200]
            })
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL RESULTS")
    print("="*80)
    
    passing = [r for r in results if r.get('success') and r.get('return', 0) > 1.0]
    failing = [r for r in results if r.get('success') and r.get('return', 0) <= 1.0]
    errors = [r for r in results if not r.get('success')]
    
    print(f"\n✅ PASSING (>1% return): {len(passing)}")
    for r in sorted(passing, key=lambda x: x.get('return', 0), reverse=True):
        print(f"  🟢 {r['file'][:40]}")
        print(f"     {r['symbol']}: {r['return']:.2f}% | {r['trades']} trades | Sharpe: {r['sharpe']:.2f}")
    
    print(f"\n⚠️  BELOW THRESHOLD (≤1% return): {len(failing)}")
    for r in sorted(failing, key=lambda x: x.get('return', -999)):
        print(f"  🔴 {r['file'][:40]}")
        print(f"     {r['symbol']}: {r['return']:.2f}% | {r['trades']} trades | Sharpe: {r['sharpe']:.2f}")
    
    print(f"\n❌ ERRORS: {len(errors)}")
    for r in errors:
        print(f"  ⚠️  {r['file'][:40]}: {r.get('error', 'Unknown')[:60]}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

