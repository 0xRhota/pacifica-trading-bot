#!/usr/bin/env python3
"""
Strategy Discovery Health Check
Verify discovery system is working correctly

Usage:
    python3 rbi_agent/health_check.py
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def check_process_running():
    """Check if discovery process is running"""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    running = "auto_discover_strategies.py" in result.stdout
    return running


def check_log_file():
    """Check if log file exists and has recent entries"""
    log_file = Path("logs/rbi_auto_discovery.log")
    
    if not log_file.exists():
        return False, "Log file does not exist"
    
    # Check last modified time
    mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
    age_minutes = (datetime.now() - mod_time).total_seconds() / 60
    
    if age_minutes > 60:
        return False, f"Log file stale ({age_minutes:.1f} minutes old)"
    
    # Check file size
    if log_file.stat().st_size == 0:
        return False, "Log file is empty"
    
    return True, f"Log file active (last update: {age_minutes:.1f} minutes ago)"


def check_proven_strategies():
    """Check if proven strategies file exists"""
    strategies_file = Path("rbi_agent/proven_strategies.json")
    
    if not strategies_file.exists():
        return False, "Proven strategies file does not exist yet"
    
    try:
        with open(strategies_file, 'r') as f:
            strategies = json.load(f)
        
        count = len(strategies)
        return True, f"Found {count} proven strategies"
    except Exception as e:
        return False, f"Error reading strategies file: {str(e)}"


def check_rbi_agent():
    """Test RBI agent initialization"""
    try:
        import importlib.util
        rbi_agent_file = os.path.join(parent_dir, 'rbi_agent', 'rbi_agent.py')
        spec = importlib.util.spec_from_file_location("rbi_agent", rbi_agent_file)
        rbi_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rbi_module)
        RBIAgent = rbi_module.RBIAgent
        
        agent = RBIAgent()
        return True, "RBI agent initialized successfully"
    except Exception as e:
        return False, f"RBI agent initialization failed: {str(e)[:100]}"


def main():
    print("=" * 80)
    print("STRATEGY DISCOVERY HEALTH CHECK")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check process
    process_running = check_process_running()
    print(f"Discovery Process: {'✅ RUNNING' if process_running else '❌ NOT RUNNING'}")
    
    # Check log file
    log_ok, log_msg = check_log_file()
    print(f"Log File: {'✅' if log_ok else '⚠️'} {log_msg}")
    
    # Check strategies file
    strategies_ok, strategies_msg = check_proven_strategies()
    print(f"Proven Strategies: {'✅' if strategies_ok else '⚠️'} {strategies_msg}")
    
    # Check RBI agent
    agent_ok, agent_msg = check_rbi_agent()
    print(f"RBI Agent: {'✅' if agent_ok else '❌'} {agent_msg}")
    
    print()
    print("=" * 80)
    
    if process_running and log_ok and agent_ok:
        print("✅ System is HEALTHY and running")
        print("\n💡 Next steps:")
        print("   - Check logs: tail -f logs/rbi_auto_discovery.log")
        print("   - View strategies: python3 rbi_agent/show_discovered_strategies.py")
    elif not process_running:
        print("⚠️  Discovery process is not running")
        print("\n💡 Start it:")
        print("   python3 rbi_agent/auto_discover_strategies.py --hours 2")
    else:
        print("⚠️  Some issues detected - check logs")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

