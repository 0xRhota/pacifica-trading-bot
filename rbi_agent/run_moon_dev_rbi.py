#!/usr/bin/env python3
"""
Run Moon Dev RBI Agent with Cambrian Data
Prepares Cambrian CSV files and runs Moon Dev's RBI agent

Usage:
    python3 rbi_agent/run_moon_dev_rbi.py
"""

import os
import sys
import subprocess
from pathlib import Path

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from rbi_agent.cambrian_csv_adapter import CambrianCSVAdapter


def prepare_cambrian_data():
    """Prepare Cambrian CSV files for Moon Dev RBI agent"""
    print("\n" + "=" * 80)
    print("PREPARING CAMBRIAN DATA FOR MOON DEV RBI AGENT")
    print("=" * 80 + "\n")
    
    adapter = CambrianCSVAdapter()
    
    results = adapter.prepare_all_symbols(
        symbols=["SOL", "ETH", "BTC"],
        days_back=90,
        interval="15m"
    )
    
    print("\n" + "=" * 80)
    print("DATA PREPARATION RESULTS")
    print("=" * 80)
    
    success_count = 0
    for symbol, path in results.items():
        if path:
            print(f"✅ {symbol}: {path}")
            success_count += 1
        else:
            print(f"❌ {symbol}: Failed")
    
    print(f"\n✅ Prepared {success_count}/{len(results)} CSV files")
    
    if success_count == 0:
        print("\n⚠️  No CSV files created - cannot run Moon Dev RBI agent")
        return False
    
    return True


def update_moon_dev_data_path():
    """Update Moon Dev's data path to use our Cambrian CSVs"""
    moon_dev_rbi = Path(parent_dir) / "moon-dev-reference" / "src" / "agents" / "rbi_agent_pp_multi.py"
    
    if not moon_dev_rbi.exists():
        print(f"⚠️  Moon Dev RBI agent not found at: {moon_dev_rbi}")
        return False
    
    # Read the file
    with open(moon_dev_rbi, 'r') as f:
        content = f.read()
    
    # Check if data path needs updating
    # Moon Dev uses hardcoded path, we need to update it
    # Actually, we'll create symlinks or copy files to their expected location
    
    return True


def run_moon_dev_rbi():
    """Run Moon Dev's RBI agent"""
    print("\n" + "=" * 80)
    print("RUNNING MOON DEV RBI AGENT")
    print("=" * 80 + "\n")
    
    moon_dev_dir = Path(parent_dir) / "moon-dev-reference"
    rbi_script = moon_dev_dir / "src" / "agents" / "rbi_agent_pp_multi.py"
    
    if not rbi_script.exists():
        print(f"❌ Moon Dev RBI agent not found: {rbi_script}")
        return False
    
    # Change to moon-dev directory
    os.chdir(moon_dev_dir)
    
    # Run Moon Dev's RBI agent
    print(f"🚀 Running Moon Dev RBI agent...")
    print(f"📁 Working directory: {moon_dev_dir}")
    print(f"📄 Script: {rbi_script.relative_to(moon_dev_dir)}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(rbi_script.relative_to(moon_dev_dir))],
            cwd=str(moon_dev_dir),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✅ Moon Dev RBI agent completed successfully!")
            return True
        else:
            print(f"\n❌ Moon Dev RBI agent exited with code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running Moon Dev RBI agent: {e}")
        return False


def main():
    print("=" * 80)
    print("MOON DEV RBI AGENT - CAMBRIAN DATA INTEGRATION")
    print("=" * 80)
    
    # Step 1: Prepare Cambrian CSV files
    if not prepare_cambrian_data():
        print("\n❌ Failed to prepare data - exiting")
        return
    
    # Step 2: Run Moon Dev RBI agent
    # Note: May need to install dependencies first
    print("\n💡 Next steps:")
    print("   1. Install dependencies: pip install backtesting pandas-ta talib-binary")
    print("   2. Set up API keys in moon-dev-reference/.env")
    print("   3. Run: cd moon-dev-reference && python src/agents/rbi_agent_pp_multi.py")
    print("\n   Or run this script after dependencies are installed")
    
    # Uncomment to auto-run (requires dependencies installed)
    # run_moon_dev_rbi()


if __name__ == "__main__":
    main()

