#!/usr/bin/env python3
"""
Fix and run a single backtest - handles CSV column issues and multi-data tester
"""

import sys
from pathlib import Path
import pandas as pd
from backtesting import Backtest, Strategy
import talib
import numpy as np

# Read the strategy file
strategy_file = Path("moon-dev-reference/src/data/rbi_pp_multi/11_02_2025/backtests/T00_MomentumContraction_BT.py")

with open(strategy_file, 'r') as f:
    content = f.read()

# Extract just the strategy class
import re
strategy_match = re.search(r'class (\w+)\(Strategy\):.*?def next\(self\):.*?(?=\nclass|\nif __name__)', content, re.DOTALL)
if not strategy_match:
    print("Could not extract strategy class")
    sys.exit(1)

strategy_code = strategy_match.group(0)
exec(compile(strategy_code, '<string>', 'exec'))

# Get strategy class name
class_name = strategy_match.group(1)
StrategyClass = locals()[class_name]

# Load and fix CSV
csv_path = Path("moon-dev-reference/src/data/rbi/SOL-USD-15m.csv")
data = pd.read_csv(csv_path)

# Fix columns - handle any extra columns
data.columns = data.columns.str.strip().str.lower()
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])

# Ensure we have the right columns
required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
if 'datetime' not in data.columns:
    if len(data.columns) >= 6:
        data.columns = required_cols
    else:
        print(f"CSV columns: {list(data.columns)}")
        print("Fixing column mapping...")
        data.columns = required_cols[:len(data.columns)]

data['datetime'] = pd.to_datetime(data['datetime'])
data = data.set_index('datetime')

# Ensure proper column names for backtesting
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Run backtest
print(f"Running backtest with {len(data)} candles...")
bt = Backtest(data, StrategyClass, cash=1_000_000, commission=0.002)
stats = bt.run()

print("\n" + "="*80)
print("📊 BACKTEST RESULTS")
print("="*80)
print(stats)
print("="*80)

# Extract return
return_pct = stats['Return [%]']
print(f"\n✅ Return: {return_pct:.2f}%")
if return_pct > 1.0:
    print(f"🎉 PASSES 1% THRESHOLD!")
else:
    print(f"⚠️  Below 1% threshold")


