#!/usr/bin/env python3
"""
Quick Start: Moon Dev RBI Agent with Cambrian Data

Usage:
    python3 rbi_agent/quick_start_moon_dev.py
"""

import os
import sys
import subprocess
from pathlib import Path

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 80)
    print("🚀 MOON DEV RBI AGENT - QUICK START")
    print("=" * 80)
    
    # Check CSV files
    csv_dir = Path(parent_dir) / "moon-dev-reference" / "src" / "data" / "rbi"
    sol_csv = csv_dir / "SOL-USD-15m.csv"
    eth_csv = csv_dir / "ETH-USD-15m.csv"
    
    print("\n📊 Data Files:")
    print(f"  SOL: {'✅' if sol_csv.exists() else '❌'} {sol_csv}")
    print(f"  ETH: {'✅' if eth_csv.exists() else '❌'} {eth_csv}")
    
    if not sol_csv.exists() or not eth_csv.exists():
        print("\n⚠️  CSV files missing - preparing Cambrian data...")
        from rbi_agent.cambrian_csv_adapter import CambrianCSVAdapter
        adapter = CambrianCSVAdapter()
        adapter.prepare_all_symbols(["SOL", "ETH"], days_back=90, interval="15m")
    
    # Check ideas file
    ideas_file = Path(parent_dir) / "moon-dev-reference" / "src" / "data" / "rbi_pp_multi" / "ideas.txt"
    print(f"\n📝 Strategy Ideas: {'✅' if ideas_file.exists() else '❌'} {ideas_file}")
    
    if ideas_file.exists():
        with open(ideas_file) as f:
            lines = len(f.readlines())
        print(f"   {lines} strategies ready")
    
    # Check dependencies
    print("\n📦 Dependencies:")
    try:
        import backtesting
        print("  ✅ backtesting")
    except:
        print("  ❌ backtesting (pip install backtesting)")
    
    try:
        import pandas_ta
        print("  ✅ pandas-ta")
    except:
        print("  ❌ pandas-ta (pip install pandas-ta)")
    
    try:
        import termcolor
        print("  ✅ termcolor")
    except:
        print("  ❌ termcolor (pip install termcolor)")
    
    # Ready to run?
    print("\n" + "=" * 80)
    print("🎯 READY TO RUN!")
    print("=" * 80)
    
    moon_dev_dir = Path(parent_dir) / "moon-dev-reference"
    rbi_script = moon_dev_dir / "src" / "agents" / "rbi_agent_pp_multi.py"
    
    print(f"\n💡 To run Moon Dev RBI agent:")
    print(f"   cd {moon_dev_dir}")
    print(f"   python {rbi_script.relative_to(moon_dev_dir)}")
    print(f"\n   Or run setup script:")
    print(f"   python3 rbi_agent/setup_moon_dev_rbi.py")
    
    print("\n📊 Expected Results:")
    print(f"   - Strategies saved to: {moon_dev_dir / 'src' / 'data' / 'rbi_pp_multi' / '[DATE]' / 'backtests_final'}")
    print(f"   - Stats CSV: {moon_dev_dir / 'src' / 'data' / 'rbi_pp_multi' / 'backtest_stats.csv'}")
    print(f"\n✅ Setup complete! Ready to discover optimized strategies!")


if __name__ == "__main__":
    main()


