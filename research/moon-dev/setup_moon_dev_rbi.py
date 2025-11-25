#!/usr/bin/env python3
"""
Moon Dev RBI Agent Setup & Runner
Sets up Moon Dev RBI agent with Cambrian data and runs strategy discovery

Usage:
    python3 rbi_agent/setup_moon_dev_rbi.py
"""

import os
import sys
import subprocess
from pathlib import Path

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n=== Checking Dependencies ===")
    
    required = {
        'backtesting': 'backtesting',
        'pandas_ta': 'pandas-ta',
        'talib': 'talib-binary',
        'termcolor': 'termcolor'
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"💡 Install with: pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!")
    return True


def prepare_cambrian_data():
    """Prepare Cambrian CSV files"""
    print("\n=== Preparing Cambrian Data ===")
    
    from rbi_agent.cambrian_csv_adapter import CambrianCSVAdapter
    
    adapter = CambrianCSVAdapter()
    results = adapter.prepare_all_symbols(
        symbols=["SOL", "ETH", "BTC"],
        days_back=90,
        interval="15m"
    )
    
    success = [s for s, p in results.items() if p]
    print(f"\n✅ Prepared {len(success)}/{len(results)} CSV files: {', '.join(success)}")
    
    return len(success) > 0


def update_moon_dev_paths():
    """Update Moon Dev's hardcoded paths to use our CSV files"""
    print("\n=== Updating Moon Dev Data Paths ===")
    
    moon_dev_rbi = Path(parent_dir) / "moon-dev-reference" / "src" / "agents" / "rbi_agent_pp_multi.py"
    
    if not moon_dev_rbi.exists():
        print(f"❌ Moon Dev RBI agent not found: {moon_dev_rbi}")
        return False
    
    # Read file
    with open(moon_dev_rbi, 'r') as f:
        content = f.read()
    
    # Moon Dev uses hardcoded path:
    # /Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv
    # We need to change it to our path
    
    old_path = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi"
    new_path = str(Path(parent_dir) / "moon-dev-reference" / "src" / "data" / "rbi").replace("\\", "/")
    
    if old_path in content:
        print(f"📝 Updating data path...")
        content = content.replace(old_path, new_path)
        
        # Write back
        with open(moon_dev_rbi, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated data path to: {new_path}")
        return True
    else:
        print(f"✅ Data path already updated or using different format")
        return True


def create_strategy_ideas():
    """Create strategy ideas file for Moon Dev RBI agent"""
    print("\n=== Creating Strategy Ideas ===")
    
    ideas_file = Path(parent_dir) / "moon-dev-reference" / "src" / "data" / "rbi_pp_multi" / "ideas.txt"
    ideas_file.parent.mkdir(parents=True, exist_ok=True)
    
    strategies = [
        "Buy when RSI < 30 and volume increases 30%",
        "Sell when RSI > 70 and price is above SMA(20)",
        "Buy when price crosses SMA(20) from below with high volume",
        "Buy when MACD crosses above signal line and RSI < 50",
        "Sell when MACD crosses below signal line and RSI > 50",
        "Buy when Bollinger Band lower touched and RSI < 35",
        "Sell when Bollinger Band upper touched and RSI > 65",
        "Buy when price is above SMA(50) and RSI < 40",
        "Sell when price is below SMA(50) and RSI > 60",
        "Buy when RSI < 35 and MACD histogram is positive"
    ]
    
    with open(ideas_file, 'w') as f:
        f.write('\n'.join(strategies))
    
    print(f"✅ Created {len(strategies)} strategy ideas in: {ideas_file}")
    return True


def run_moon_dev_rbi():
    """Run Moon Dev's RBI agent"""
    print("\n=== Running Moon Dev RBI Agent ===")
    
    moon_dev_dir = Path(parent_dir) / "moon-dev-reference"
    rbi_script = moon_dev_dir / "src" / "agents" / "rbi_agent_pp_multi.py"
    
    if not rbi_script.exists():
        print(f"❌ Moon Dev RBI agent not found: {rbi_script}")
        return False
    
    print(f"🚀 Starting Moon Dev RBI agent...")
    print(f"📁 Working directory: {moon_dev_dir}")
    print(f"📄 Script: {rbi_script.name}")
    print(f"\n💡 This will:")
    print(f"   - Test {len(open(moon_dev_dir / 'src' / 'data' / 'rbi_pp_multi' / 'ideas.txt').readlines())} strategies")
    print(f"   - Optimize to hit 50% target return")
    print(f"   - Save strategies that pass 1% threshold")
    print(f"   - Use Cambrian data (SOL, ETH)")
    print(f"\n⏳ Running... (this may take a while)\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(rbi_script.relative_to(moon_dev_dir))],
            cwd=str(moon_dev_dir),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✅ Moon Dev RBI agent completed successfully!")
            print(f"📊 Check results in: {moon_dev_dir / 'src' / 'data' / 'rbi_pp_multi'}")
            return True
        else:
            print(f"\n❌ Moon Dev RBI agent exited with code {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error running Moon Dev RBI agent: {e}")
        return False


def main():
    print("=" * 80)
    print("MOON DEV RBI AGENT SETUP - CAMBRIAN DATA INTEGRATION")
    print("=" * 80)
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("\n⚠️  Please install missing dependencies first")
        return
    
    # Step 2: Prepare Cambrian data
    if not prepare_cambrian_data():
        print("\n❌ Failed to prepare data - exiting")
        return
    
    # Step 3: Update Moon Dev paths
    update_moon_dev_paths()
    
    # Step 4: Create strategy ideas
    create_strategy_ideas()
    
    # Step 5: Run Moon Dev RBI agent
    print("\n" + "=" * 80)
    response = input("🚀 Ready to run Moon Dev RBI agent? (y/n): ")
    
    if response.lower() == 'y':
        run_moon_dev_rbi()
    else:
        print("\n💡 Run manually with:")
        print(f"   cd moon-dev-reference")
        print(f"   python src/agents/rbi_agent_pp_multi.py")


if __name__ == "__main__":
    main()


