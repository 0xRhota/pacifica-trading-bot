#!/usr/bin/env python3
"""
Strategy Switch Script - Clean Break Between Strategies

Usage:
    python3 scripts/general/switch_strategy.py --dex lighter --strategy "deep42-v1" --reason "Deploy Deep42 multi-timeframe integration"
    python3 scripts/general/switch_strategy.py --dex pacifica --strategy "swing-v2" --reason "Switch to longer hold times"

What this does:
1. Archives current trade tracker with strategy name + timestamp
2. Creates fresh trade tracker (clean slate)
3. Logs clear marker in bot logs
4. Creates strategy switch record in logs/strategy_switches.log

Why this matters:
- Prevents ghost positions from old strategies
- Clear performance boundaries for each strategy
- Easy rollback to previous strategy data
- Clean logs for analysis
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
import sys

def switch_strategy(dex: str, strategy_name: str, reason: str = "Strategy switch"):
    """
    Perform a clean strategy switch

    Args:
        dex: "lighter" or "pacifica"
        strategy_name: Name for this strategy (e.g., "deep42-v1", "swing-v2")
        reason: Reason for the switch
    """
    dex = dex.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Paths
    trades_dir = Path("logs/trades")
    archive_dir = trades_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    current_tracker = trades_dir / f"{dex}.json"
    archive_file = archive_dir / f"{dex}_{strategy_name}_{timestamp}.json"

    switch_log = Path("logs/strategy_switches.log")

    print("\n" + "=" * 70)
    print("🔄 STRATEGY SWITCH")
    print("=" * 70)
    print(f"DEX:      {dex.upper()}")
    print(f"Strategy: {strategy_name}")
    print(f"Reason:   {reason}")
    print(f"Time:     {datetime.now().isoformat()}")
    print("=" * 70 + "\n")

    # Step 1: Archive current tracker
    if current_tracker.exists():
        # Load stats before archiving
        with open(current_tracker, 'r') as f:
            trades = json.load(f)

        open_trades = [t for t in trades if t.get('status') == 'open']
        closed_trades = [t for t in trades if t.get('status') == 'closed']

        print(f"📦 Archiving current tracker...")
        print(f"   - Total trades: {len(trades)}")
        print(f"   - Open: {len(open_trades)}")
        print(f"   - Closed: {len(closed_trades)}")
        print(f"   - Archive: {archive_file}")

        # Copy to archive
        shutil.copy2(current_tracker, archive_file)
        print(f"   ✅ Archived to {archive_file}\n")

        # Step 2: Create fresh tracker
        print(f"🆕 Creating fresh tracker...")
        with open(current_tracker, 'w') as f:
            json.dump([], f, indent=2)
        print(f"   ✅ Fresh tracker created\n")
    else:
        print(f"ℹ️  No existing tracker found - creating new one\n")
        trades_dir.mkdir(parents=True, exist_ok=True)
        with open(current_tracker, 'w') as f:
            json.dump([], f, indent=2)

    # Step 3: Log the switch
    switch_record = {
        "timestamp": datetime.now().isoformat(),
        "dex": dex,
        "strategy": strategy_name,
        "reason": reason,
        "archived_to": str(archive_file) if current_tracker.exists() else None
    }

    print(f"📝 Logging strategy switch...")

    # Create/append to switch log
    switches = []
    if switch_log.exists():
        with open(switch_log, 'r') as f:
            switches = json.load(f)

    switches.append(switch_record)

    with open(switch_log, 'w') as f:
        json.dump(switches, f, indent=2)

    print(f"   ✅ Logged to {switch_log}\n")

    # Step 4: Create clear log marker
    bot_log = Path(f"logs/{dex}_bot.log")
    if bot_log.exists():
        print(f"📍 Adding marker to bot log...")
        marker = f"\n{'=' * 80}\n"
        marker += f"🔄 STRATEGY SWITCH: {strategy_name}\n"
        marker += f"Time: {datetime.now().isoformat()}\n"
        marker += f"Reason: {reason}\n"
        marker += f"Old tracker archived to: {archive_file}\n"
        marker += f"Fresh tracker created - clean slate\n"
        marker += f"{'=' * 80}\n\n"

        with open(bot_log, 'a') as f:
            f.write(marker)
        print(f"   ✅ Marker added to {bot_log}\n")

    print("=" * 70)
    print("✅ STRATEGY SWITCH COMPLETE")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Verify bot is stopped: pgrep -f 'bot_{dex}'")
    print(f"2. Start bot with new strategy")
    print(f"3. Monitor first few cycles in logs/{dex}_bot.log")
    print(f"4. Verify clean start with no ghost positions")
    print("\n")

    return {
        "success": True,
        "archive_file": str(archive_file),
        "switch_record": switch_record
    }


def main():
    parser = argparse.ArgumentParser(
        description="Perform clean strategy switch with trade tracker archiving"
    )
    parser.add_argument(
        "--dex",
        required=True,
        choices=["lighter", "pacifica", "hibachi", "extended"],
        help="DEX to switch strategy for"
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Strategy name (e.g., 'deep42-v1', 'swing-v2')"
    )
    parser.add_argument(
        "--reason",
        default="Strategy switch",
        help="Reason for the switch"
    )

    args = parser.parse_args()

    try:
        result = switch_strategy(args.dex, args.strategy, args.reason)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
