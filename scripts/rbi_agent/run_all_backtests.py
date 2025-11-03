#!/usr/bin/env python3
"""
Run all Moon Dev RBI backtest files and extract results
Shows which strategies pass the 1% threshold
"""

import subprocess
import re
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime

# Project root
project_root = Path(__file__).parent.parent.parent
backtest_dir = project_root / "moon-dev-reference/src/data/rbi_pp_multi/11_02_2025/backtests"

def extract_return_percent(output: str) -> float:
    """Extract Return [%] from backtest output"""
    match = re.search(r'Return \[%\]\s+([-\d.]+)', output)
    if match:
        return float(match.group(1))
    return None

def extract_stats(output: str) -> dict:
    """Extract key stats from backtest output"""
    stats = {}
    
    # Return [%]
    match = re.search(r'Return \[%\]\s+([-\d.]+)', output)
    if match:
        stats['return'] = float(match.group(1))
    
    # Buy & Hold Return [%]
    match = re.search(r'Buy & Hold Return \[%\]\s+([-\d.]+)', output)
    if match:
        stats['buy_hold'] = float(match.group(1))
    
    # Sharpe Ratio
    match = re.search(r'Sharpe Ratio\s+([-\d.]+)', output)
    if match:
        stats['sharpe'] = float(match.group(1))
    
    # Max Drawdown
    match = re.search(r'Max\. Drawdown \[%\]\s+([-\d.]+)', output)
    if match:
        stats['max_dd'] = float(match.group(1))
    
    # Number of trades
    match = re.search(r'# Trades\s+(\d+)', output)
    if match:
        stats['trades'] = int(match.group(1))
    
    # Win Rate
    match = re.search(r'Win Rate \[%\]\s+([-\d.]+)', output)
    if match:
        stats['win_rate'] = float(match.group(1))
    
    return stats

def run_backtest(file_path: Path) -> dict:
    """Run a single backtest file and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {file_path.name}")
    print('='*80)
    
    try:
        # Read and patch the file to skip multi-data tester (which doesn't exist)
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Patch the file to fix issues
        patched_content = content
        
        # 1. Fix CSV column handling (trailing comma issue)
        patched_content = re.sub(
            r"data\.columns = \['Open', 'High', 'Low', 'Close', 'Volume'\]",
            """# Fix columns - handle trailing comma
data.columns = data.columns.str.strip().str.lower()
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower() or col.strip() == ''])
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']""",
            patched_content
        )
        
        # 2. Comment out multi-data tester (doesn't exist)
        if 'from multi_data_tester import' in patched_content:
            patched_content = re.sub(
                r'from multi_data_tester import.*',
                '# from multi_data_tester import test_on_all_data  # Skipped - module not available',
                patched_content
            )
            patched_content = re.sub(
                r'results = test_on_all_data\([^)]+\)',
                '# results = test_on_all_data(...)  # Skipped',
                patched_content
            )
            patched_content = re.sub(
                r'if results is not None:.*?else:.*?print\([^)]+\)',
                '# Multi-data testing skipped',
                patched_content,
                flags=re.DOTALL
            )
        
        # Write patched version to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(patched_content)
            tmp_path = tmp.name
        
        file_to_run = tmp_path
        
        # Change to moon-dev-reference directory for imports
        result = subprocess.run(
            ['python3', file_to_run],
            cwd=str(file_path.parent.parent.parent.parent),
            capture_output=True,
            text=True,
            timeout=120  # 2 min timeout per backtest
        )
        
        # Clean up temp file if we created one
        if file_to_run != str(file_path) and os.path.exists(file_to_run):
            os.unlink(file_to_run)
        
        stdout = result.stdout
        stderr = result.stderr
        
        if result.returncode != 0:
            return {
                'file': file_path.name,
                'success': False,
                'error': stderr[:200] if stderr else 'Unknown error',
                'return': None
            }
        
        # Extract stats
        stats = extract_stats(stdout)
        
        # Print key output
        if 'Return [%]' in stdout:
            print(stdout[stdout.find('Return [%]'):stdout.find('Return [%]')+500])
        
        return {
            'file': file_path.name,
            'success': True,
            'stats': stats,
            'return': stats.get('return'),
            'output': stdout[-1000:]  # Last 1000 chars
        }
        
    except subprocess.TimeoutExpired:
        return {
            'file': file_path.name,
            'success': False,
            'error': 'Timeout (120s)',
            'return': None
        }
    except Exception as e:
        return {
            'file': file_path.name,
            'success': False,
            'error': str(e)[:200],
            'return': None
        }

def main():
    print("\n" + "="*80)
    print("🚀 RUNNING ALL RBI BACKTESTS")
    print("="*80)
    print(f"Backtest directory: {backtest_dir}")
    print(f"Threshold: >1% return to save")
    print("="*80)
    
    # Find all backtest files
    backtest_files = sorted(backtest_dir.glob("T*.py"))
    
    if not backtest_files:
        print(f"❌ No backtest files found in {backtest_dir}")
        return
    
    print(f"\n📊 Found {len(backtest_files)} backtest files\n")
    
    # Run all backtests
    results = []
    for file_path in backtest_files:
        result = run_backtest(file_path)
        results.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80)
    
    passing = []
    failing = []
    errors = []
    
    for r in results:
        if not r['success']:
            errors.append(r)
        elif r['return'] is not None:
            if r['return'] > 1.0:
                passing.append(r)
            else:
                failing.append(r)
        else:
            errors.append(r)
    
    print(f"\n✅ PASSING (>1% return): {len(passing)}")
    for r in sorted(passing, key=lambda x: x['return'] or 0, reverse=True):
        stats = r.get('stats', {})
        print(f"  🟢 {r['file'][:50]}")
        print(f"     Return: {r['return']:.2f}% | Trades: {stats.get('trades', 0)} | Sharpe: {stats.get('sharpe', 0):.2f}")
    
    print(f"\n⚠️  BELOW THRESHOLD (≤1% return): {len(failing)}")
    for r in sorted(failing, key=lambda x: x['return'] or -999):
        stats = r.get('stats', {})
        print(f"  🔴 {r['file'][:50]}")
        print(f"     Return: {r['return']:.2f}% | Trades: {stats.get('trades', 0)} | Sharpe: {stats.get('sharpe', 0):.2f}")
    
    print(f"\n❌ ERRORS: {len(errors)}")
    for r in errors:
        print(f"  ⚠️  {r['file'][:50]}")
        print(f"     Error: {r.get('error', 'Unknown')[:100]}")
    
    print("\n" + "="*80)
    print(f"✅ Total: {len(results)} | Passing: {len(passing)} | Failing: {len(failing)} | Errors: {len(errors)}")
    print("="*80)
    
    # Save results to JSON
    import json
    results_file = project_root / "rbi_agent" / "backtest_results_summary.json"
    results_file.parent.mkdir(exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'passing': len(passing),
            'failing': len(failing),
            'errors': len(errors),
            'results': results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    main()

