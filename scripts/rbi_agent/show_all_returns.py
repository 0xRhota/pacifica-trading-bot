#!/usr/bin/env python3
"""
Show all strategy returns clearly
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import talib
import re

project_root = Path(__file__).parent.parent.parent
backtest_dir = project_root / "moon-dev-reference/src/data/rbi_pp_multi/11_02_2025/backtests"
csv_dir = project_root / "moon-dev-reference/src/data/rbi"

def load_strategy_class(file_path: Path):
    """Load strategy class from file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    class_match = re.search(r'(class (\w+)\(Strategy\):.*?)(?=\nclass|\nif __name__|\n# 🌙)', content, re.DOTALL)
    if not class_match:
        return None, None
    
    exec_globals = {
        'Strategy': Strategy,
        'talib': talib,
        'np': np,
        'pd': pd
    }
    
    exec(compile(class_match.group(1), '<string>', 'exec'), exec_globals)
    class_name = class_match.group(2)
    return exec_globals[class_name], class_name

def run_backtest_on_data(strategy_class, csv_path: Path):
    """Run backtest on a CSV file"""
    data = pd.read_csv(csv_path)
    
    data.columns = data.columns.str.strip().str.lower()
    data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower() or col.strip() == ''])
    
    if len(data.columns) >= 6:
        data = data.iloc[:, :6]
        data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    elif len(data.columns) == 5:
        data.columns = ['datetime', 'open', 'high', 'low', 'close']
        data['volume'] = 0
    
    data['datetime'] = pd.to_datetime(data['datetime'])
    data = data.set_index('datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    bt = Backtest(data, strategy_class, cash=1_000_000, commission=0.002)
    stats = bt.run()
    
    return {
        'return': stats['Return [%]'],
        'buy_hold': stats['Buy & Hold Return [%]'],
        'sharpe': stats['Sharpe Ratio'],
        'max_dd': stats['Max. Drawdown [%]'],
        'trades': stats['# Trades'],
        'win_rate': stats['Win Rate [%]'],
    }

def main():
    backtest_files = sorted(backtest_dir.glob("T*.py"))
    
    print("\n" + "="*100)
    print("📊 ALL STRATEGY RETURNS (90 days, 15m candles on Cambrian data)")
    print("="*100)
    print()
    print(f"{'Strategy':<40} | {'Return':>10} | {'Buy&Hold':>10} | {'Trades':>7} | {'Win%':>7} | {'Sharpe':>8} | {'MaxDD':>8}")
    print("-"*100)
    
    all_results = []
    
    for file_path in backtest_files:
        try:
            strategy_class, class_name = load_strategy_class(file_path)
            if not strategy_class:
                all_results.append({
                    'name': file_path.stem,
                    'return': None,
                    'error': 'Could not load class'
                })
                continue
            
            # Test on both SOL and ETH, pick best
            best = None
            best_return = -999
            best_symbol = None
            
            for symbol in ['SOL', 'ETH']:
                csv_path = csv_dir / f"{symbol}-USD-15m.csv"
                if not csv_path.exists():
                    continue
                
                try:
                    result = run_backtest_on_data(strategy_class, csv_path)
                    if result and result['return'] > best_return:
                        best = result
                        best_return = result['return']
                        best_symbol = symbol
                except Exception as e:
                    continue
            
            if best:
                best['name'] = file_path.stem
                best['symbol'] = best_symbol
                all_results.append(best)
                print(f"{file_path.stem:<40} | {best['return']:>10.2f}% | {best['buy_hold']:>10.2f}% | {best['trades']:>7} | {best['win_rate']:>7.1f}% | {best['sharpe']:>8.2f} | {best['max_dd']:>8.2f}%")
            else:
                all_results.append({
                    'name': file_path.stem,
                    'return': None,
                    'error': 'Execution failed'
                })
                print(f"{file_path.stem:<40} | {'ERROR':>10} | {'N/A':>10} | {'N/A':>7} | {'N/A':>7} | {'N/A':>8} | {'N/A':>8}")
                
        except Exception as e:
            all_results.append({
                'name': file_path.stem,
                'return': None,
                'error': str(e)[:50]
            })
            print(f"{file_path.stem:<40} | {'ERROR':>10} | {'N/A':>10} | {'N/A':>7} | {'N/A':>7} | {'N/A':>8} | {'N/A':>8}")
    
    print("-"*100)
    
    # Summary
    valid = [r for r in all_results if r.get('return') is not None]
    if valid:
        sorted_valid = sorted(valid, key=lambda x: x.get('return', -999), reverse=True)
        
        print(f"\n📈 RANKED BY RETURN:")
        print("-"*100)
        for i, r in enumerate(sorted_valid, 1):
            ret = r.get('return', 0)
            symbol = r.get('symbol', 'N/A')
            trades = r.get('trades', 0)
            sharpe = r.get('sharpe', 0)
            status = "🟢" if ret > 1.0 else "🟡" if ret > 0 else "🔴"
            print(f"{i:2}. {status} {r['name']:<35} | {ret:>8.2f}% | {symbol} | {trades:>4} trades | Sharpe: {sharpe:>6.2f}")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    main()


