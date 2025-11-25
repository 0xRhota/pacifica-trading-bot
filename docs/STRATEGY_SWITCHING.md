# Strategy Switching Guide

**Purpose**: Perform clean breaks between different trading strategies to prevent ghost positions, sync issues, and messy logs.

---

## Why Clean Strategy Switches Matter

### Problems Without Clean Breaks
1. **Ghost Positions**: Old positions remain in tracker after strategy changes
2. **Sync Issues**: Tracker out of sync with exchange reality
3. **Messy Performance Tracking**: Can't tell which strategy caused which P&L
4. **Unclear Logs**: Hard to identify when strategy changes happened

### Benefits of Clean Breaks
1. ✅ **No Ghost Positions**: Fresh tracker starts with clean slate
2. ✅ **Clear Performance Boundaries**: Each strategy has isolated performance data
3. ✅ **Easy Rollback**: Old strategy data archived and accessible
4. ✅ **Clear Log Markers**: Easy to identify strategy changes in logs

---

## When to Switch Strategies

Perform a clean strategy switch when:

1. **Major Strategy Changes**
   - Switching from momentum to mean reversion
   - Changing from swing to scalping
   - Adding/removing major data sources (e.g., Deep42 integration)

2. **Prompt Changes**
   - Major prompt revisions
   - Switching between prompt versions (v1 → v2)
   - Changing LLM instructions significantly

3. **Configuration Changes**
   - Changing position sizing dramatically
   - Modifying max positions limit
   - Adjusting risk parameters

4. **After Sync Issues**
   - Ghost positions detected
   - Tracker desynchronization
   - Data corruption

---

## Strategy Switch Process

### Step 1: Stop the Bot

```bash
# Check if bot is running
pgrep -f "bot_lighter"    # For Lighter
pgrep -f "bot_pacifica"   # For Pacifica

# Stop the bot
pkill -f "lighter_agent.bot_lighter"   # For Lighter
pkill -f "pacifica_agent.bot_pacifica" # For Pacifica

# Verify stopped
pgrep -f "bot_lighter"    # Should return nothing
```

### Step 2: Run Strategy Switch Script

```bash
# Lighter bot
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "strategy-name" \
  --reason "Brief reason for switch"

# Pacifica bot
python3 scripts/general/switch_strategy.py \
  --dex pacifica \
  --strategy "strategy-name" \
  --reason "Brief reason for switch"
```

**Strategy Naming Convention**: Use descriptive names like:
- `deep42-v1` - Deep42 multi-timeframe integration
- `swing-v2` - Longer hold times
- `momentum-short` - Momentum with short holds
- `vwap-v1` - VWAP-based strategy

### Step 3: Verify Archive Created

```bash
# Check archive was created
ls -lh logs/trades/archive/

# Should see: lighter_strategy-name_TIMESTAMP.json
```

### Step 4: Start Bot with Clean Slate

```bash
# Lighter bot
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# Pacifica bot
nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 > logs/pacifica_bot.log 2>&1 &

# Get new PID
pgrep -f "bot_lighter"    # Note the new PID
```

### Step 5: Monitor First Cycles

```bash
# Watch logs for clean start
tail -f logs/lighter_bot.log

# Look for:
# - ✅ Strategy switch marker at top
# - ✅ No "STALE POSITION" warnings
# - ✅ No "Failed to close" errors
# - ✅ Clean decision cycles
```

### Step 6: Verify Clean Start

```bash
# After 2-3 cycles, check for ghost positions
tail -200 logs/lighter_bot.log | grep -E "(STALE|ghost|failed to close)" || echo "✅ Clean start!"

# Verify fresh tracker
python3 -c "from trade_tracker import TradeTracker; t = TradeTracker('lighter'); print(f'Open: {len(t.get_open_trades())}, Closed: {len(t.get_closed_trades())}')"
# Should show: Open: 0-2, Closed: 0 (or very few)
```

---

## What the Script Does

1. **Archives Current Tracker**
   - Copies `logs/trades/<dex>.json` → `logs/trades/archive/<dex>_<strategy>_<timestamp>.json`
   - Preserves all trade history from previous strategy
   - Logs stats (total trades, open, closed)

2. **Creates Fresh Tracker**
   - Replaces `logs/trades/<dex>.json` with empty array `[]`
   - Clean slate for new strategy

3. **Logs the Switch**
   - Records switch in `logs/strategy_switches.log`
   - Includes: timestamp, dex, strategy name, reason, archive location

4. **Adds Clear Log Marker**
   - Appends visible marker to `logs/<dex>_bot.log`
   - Makes strategy changes easy to identify in logs

---

## Strategy Switch Log

All strategy switches are recorded in `logs/strategy_switches.log`:

```json
[
  {
    "timestamp": "2025-11-13T11:23:24.836641",
    "dex": "lighter",
    "strategy": "deep42-v1",
    "reason": "Deploy Deep42 multi-timeframe integration - clean break from previous strategy",
    "archived_to": "logs/trades/archive/lighter_deep42-v1_20251113_112324.json"
  }
]
```

This log provides:
- Complete history of all strategy changes
- When each change happened
- Why it happened
- Where the old data is archived

---

## Accessing Old Strategy Data

### View Archived Trades

```bash
# List all archives
ls -lh logs/trades/archive/

# View specific archive
python3 -c "
import json
with open('logs/trades/archive/lighter_deep42-v1_20251113_112324.json') as f:
    trades = json.load(f)
    closed = [t for t in trades if t['status'] == 'closed']
    print(f'Total trades: {len(trades)}, Closed: {len(closed)}')
"
```

### Compare Strategy Performance

```bash
# Current strategy
python3 -c "from trade_tracker import TradeTracker; TradeTracker('lighter').print_stats()"

# Old strategy (from archive)
python3 -c "
import json
from pathlib import Path

archive_file = 'logs/trades/archive/lighter_old-strategy_20251113_112324.json'
with open(archive_file) as f:
    trades = json.load(f)
    closed = [t for t in trades if t.get('status') == 'closed']
    wins = [t for t in closed if t.get('pnl', 0) > 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed)

    print(f'Strategy: {Path(archive_file).stem}')
    print(f'Total Trades: {len(closed)}')
    print(f'Win Rate: {len(wins)/len(closed):.1%}')
    print(f'Total P&L: ${total_pnl:.2f}')
"
```

---

## Rollback to Previous Strategy

If new strategy isn't working, rollback to previous:

```bash
# 1. Stop bot
pkill -f "lighter_agent.bot_lighter"

# 2. Restore old tracker (swap files)
mv logs/trades/lighter.json logs/trades/lighter_failed_strategy.json.backup
cp logs/trades/archive/lighter_old-strategy_TIMESTAMP.json logs/trades/lighter.json

# 3. Revert code changes if needed
# (e.g., undo prompt changes, config changes)

# 4. Restart bot
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# 5. Document rollback
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "rollback-to-old-strategy" \
  --reason "New strategy underperformed, rolling back"
```

---

## Examples

### Example 1: Deploy Deep42 Integration

```bash
# Stop bot
pkill -f "lighter_agent.bot_lighter"

# Clean switch
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "deep42-v1" \
  --reason "Deploy Deep42 multi-timeframe integration - clean break from previous strategy"

# Start bot
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# Monitor
tail -f logs/lighter_bot.log
```

### Example 2: Switch from V1 to V2 Prompt

```bash
# Stop bot
pkill -f "pacifica_agent.bot_pacifica"

# Switch strategy
python3 scripts/general/switch_strategy.py \
  --dex pacifica \
  --strategy "v2-deep-reasoning" \
  --reason "Switch to V2 prompt with deep reasoning chain"

# Start bot (code should already have V2 prompt enabled)
nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 > logs/pacifica_bot.log 2>&1 &
```

### Example 3: Fix Sync Issues

```bash
# Stop bot
pkill -f "lighter_agent.bot_lighter"

# Clean switch (clears ghost positions)
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "sync-fix-$(date +%Y%m%d)" \
  --reason "Fix trade tracker sync issues - 21 ghost positions cleared"

# Start bot
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

---

## Best Practices

1. **Always Stop Bot First**: Don't switch strategies while bot is running
2. **Use Descriptive Names**: Make strategy names clear and meaningful
3. **Document Reasons**: Always provide a reason for the switch
4. **Monitor First Cycles**: Watch logs for at least 2-3 cycles after switch
5. **Keep Archives**: Never delete archived trade data
6. **Log Markers**: Verify strategy switch marker appears in logs
7. **Clean Start Verification**: Check for ghost position errors after restart

---

## Troubleshooting

### Bot Still Showing Ghost Positions

```bash
# Verify tracker is actually empty
cat logs/trades/lighter.json
# Should be: []

# If not empty, manually clear:
echo '[]' > logs/trades/lighter.json

# Restart bot
pkill -f "lighter_agent.bot_lighter"
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

### Archive Not Created

```bash
# Manually create archive if needed
mkdir -p logs/trades/archive
cp logs/trades/lighter.json logs/trades/archive/lighter_manual_$(date +%Y%m%d_%H%M%S).json
echo '[]' > logs/trades/lighter.json
```

### Lost Trade Data

```bash
# All archives are in logs/trades/archive/
ls -lh logs/trades/archive/

# Restore from archive if needed
cp logs/trades/archive/lighter_STRATEGY_TIMESTAMP.json logs/trades/lighter.json
```

---

**Last Updated**: 2025-11-13
**Script Location**: `scripts/general/switch_strategy.py`
**Switch Log**: `logs/strategy_switches.log`
**Archives**: `logs/trades/archive/`
