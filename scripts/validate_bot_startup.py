#!/usr/bin/env python3
"""
Bulletproof Bot Startup Validator
Checks first cycle output to ensure all data is being logged correctly
"""
import time
import subprocess
import sys

def check_log_for_data():
    """Check if log contains required data"""
    time.sleep(90)  # Wait for first cycle

    with open('logs/llm_bot.log', 'r') as f:
        log = f.read()

    required_data = {
        'Market Data Summary': 'MARKET DATA SUMMARY:',
        'Price Column': 'Price',
        'Volume Column': '24h Vol',
        'Funding Column': 'Funding',
        'OI Column': 'OI',
        'RSI Column': 'RSI',
        'MACD Column': 'MACD',
        'SMA Column': 'SMA20>50',
        'Deep42 Query': 'Generated Deep42 query:',
        'LLM Decision': 'LLM DECISION:',
    }

    missing = []
    for name, pattern in required_data.items():
        if pattern not in log:
            missing.append(name)

    if missing:
        print(f"❌ VALIDATION FAILED - Missing: {', '.join(missing)}")
        print("\n=== LOG EXCERPT ===")
        print(log[-2000:])
        return False

    print("✅ VALIDATION PASSED - All data present in logs")

    # Show sample
    lines = log.split('\n')
    for i, line in enumerate(lines):
        if 'MARKET DATA SUMMARY' in line:
            print("\n=== MARKET DATA SAMPLE ===")
            for j in range(i, min(i+10, len(lines))):
                print(lines[j])
            break

    return True

if __name__ == "__main__":
    print("🔍 Validating bot startup...")
    success = check_log_for_data()
    sys.exit(0 if success else 1)
