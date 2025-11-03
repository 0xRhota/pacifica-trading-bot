#!/usr/bin/env python3
"""
Moon Dev RBI Agent Monitor
Check status and progress of running Moon Dev RBI agent

Usage:
    python3 rbi_agent/monitor_moon_dev_rbi.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_process():
    """Check if Moon Dev RBI agent is running"""
    import subprocess
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    running = "rbi_agent_pp_multi.py" in result.stdout
    return running


def check_logs():
    """Check recent log activity"""
    log_file = Path(parent_dir) / "logs" / "moon_dev_rbi.log"
    
    if not log_file.exists():
        return False, "Log file does not exist"
    
    # Check last modified time
    mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
    age_seconds = (datetime.now() - mod_time).total_seconds()
    
    if age_seconds > 300:  # 5 minutes
        return False, f"Log file stale ({age_seconds/60:.1f} minutes old)"
    
    # Check file size
    size = log_file.stat().st_size
    if size == 0:
        return False, "Log file is empty"
    
    return True, f"Log file active ({size/1024:.1f} KB, updated {age_seconds:.0f}s ago)"


def check_results():
    """Check if results are being generated"""
    moon_dev_dir = Path(parent_dir) / "moon-dev-reference"
    stats_csv = moon_dev_dir / "src" / "data" / "rbi_pp_multi" / "backtest_stats.csv"
    
    if stats_csv.exists():
        # Count strategies
        import csv
        try:
            with open(stats_csv, 'r') as f:
                reader = csv.DictReader(f)
                count = sum(1 for _ in reader)
            return True, f"Found {count} strategies in results"
        except:
            return True, "Results file exists"
    else:
        return False, "No results file yet"


def check_backtest_files():
    """Check for generated backtest files"""
    moon_dev_dir = Path(parent_dir) / "moon-dev-reference"
    rbi_dir = moon_dev_dir / "src" / "data" / "rbi_pp_multi"
    
    if not rbi_dir.exists():
        return 0
    
    # Count Python backtest files
    py_files = list(rbi_dir.rglob("*.py"))
    return len(py_files)


def main():
    print("=" * 80)
    print("MOON DEV RBI AGENT - STATUS MONITOR")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check process
    process_running = check_process()
    print(f"Process: {'✅ RUNNING' if process_running else '❌ NOT RUNNING'}")
    
    # Check logs
    log_ok, log_msg = check_logs()
    print(f"Logs: {'✅' if log_ok else '⚠️'} {log_msg}")
    
    # Check results
    results_ok, results_msg = check_results()
    print(f"Results: {'✅' if results_ok else '⏳'} {results_msg}")
    
    # Check backtest files
    file_count = check_backtest_files()
    print(f"Backtest Files: {file_count}")
    
    print("\n" + "=" * 80)
    
    if process_running and log_ok:
        print("✅ Moon Dev RBI agent is RUNNING and ACTIVE")
        print("\n💡 Monitor progress:")
        print("   tail -f logs/moon_dev_rbi.log")
        print("\n💡 Check results:")
        print("   python3 rbi_agent/show_moon_dev_results.py")
    elif not process_running:
        print("⚠️  Moon Dev RBI agent is NOT running")
        print("\n💡 Start it:")
        print("   cd moon-dev-reference")
        print("   python src/agents/rbi_agent_pp_multi.py")
    else:
        print("⚠️  Some issues detected - check logs")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

