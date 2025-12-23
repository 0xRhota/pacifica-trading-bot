# Fast Exit Monitor Implementation

**Date**: 2025-11-28
**Status**: Implemented

## Problem Statement

User observation: "Position goes up immediately after opening, then might be down 5 mins later."

With 5-minute LLM decision cycles:
- Average exit delay: 2.5 minutes
- Best case: Immediate (if LLM cycle happens to run)
- Worst case: 5 minutes

This means we could miss TP/SL hits by minutes, allowing winning trades to turn into losses.

## Solution: Fast Exit Monitor

A **separate monitoring loop** that:
1. Runs every 30 seconds
2. Only checks prices against TP/SL/trailing rules
3. Makes NO LLM calls (FREE operation)
4. Closes positions immediately when exit rules trigger

### Architecture

```
Main Bot Loop (5 min)              Fast Exit Monitor (30 sec)
      │                                    │
      ├─ Fetch market data                 ├─ Fetch positions
      ├─ Get LLM decision         ║        ├─ Fetch current prices
      ├─ Execute entries/exits    ║        ├─ Check exit rules
      ├─ Sleep 5 min              ║        ├─ Execute closes if triggered
      │                           ║        ├─ Sleep 30 sec
      └─ (repeat)                          └─ (repeat)
                                  ║
                          Both run concurrently
                          as asyncio tasks
```

### Cost Analysis

| Component | Before | After |
|-----------|--------|-------|
| LLM calls | Every 5 min | Every 5 min (unchanged) |
| Price API calls | Every 5 min | Every 30 sec |
| Exit latency | 0-300s (avg 150s) | 0-30s (avg 15s) |
| Additional cost | $0 | ~$0 (price APIs are free) |

**10x faster exit reactions at zero additional LLM cost.**

## Implementation Details

### Files Created

1. `hibachi_agent/execution/fast_exit_monitor.py`
   - FastExitMonitor class for Hibachi
   - Uses StrategyAExitRules (TIME_CAPPED)
   - 30 second check interval

2. `extended_agent/execution/fast_exit_monitor.py`
   - FastExitMonitor class for Extended
   - Uses StrategyBExitRules (RUNNERS_RUN)
   - 30 second check interval
   - **Critical for trailing stops**: Updates peak P/L every 30s

### Files Modified

1. `hibachi_agent/bot_hibachi.py`
   - Added import for FastExitMonitor
   - Initialize monitor in __init__
   - Start as asyncio task in run()
   - Graceful shutdown on exit

2. `extended_agent/bot_extended.py`
   - Same changes as Hibachi
   - Trailing stop monitoring especially important here

## Strategy Tracking

### Before (2025-11-27)

| Bot | Strategy | Exit Check Frequency |
|-----|----------|---------------------|
| Hibachi | STRATEGY_A_TIME_CAPPED | Every 5 min |
| Extended | STRATEGY_B_RUNNERS_RUN | Every 5 min |

### After (2025-11-28)

| Bot | Strategy | Exit Check Frequency |
|-----|----------|---------------------|
| Hibachi | STRATEGY_A_TIME_CAPPED + FAST_EXIT | Every 30 sec |
| Extended | STRATEGY_B_RUNNERS_RUN + FAST_EXIT | Every 30 sec |

## Switchover Process

1. Stop running bots
2. Deploy updated code
3. Start bots - fast exit monitor starts automatically
4. Monitor logs for `[FAST-EXIT]` entries

## Rollback

To disable fast exit monitoring without code changes, set `enabled=False`:

```python
self.fast_exit_monitor = FastExitMonitor(
    ...
    enabled=False  # Disables monitoring
)
```

## Monitoring

Look for these log entries:

```
⚡ Fast exit monitor started (30s price checks)
[FAST-EXIT] Check #1 | Exits triggered: 0
⚡ [FAST-EXIT] BTC/USDT-P triggered: TAKE PROFIT: +4.52%
   ✅ Fast exit executed successfully
```

Stats logged every 30 minutes:
```
[FAST-EXIT STATS]
  Status: Running
  Checks: 180
  Exits: 3
  Trailing Activations: 2 (Extended only)
  Last Check: 2025-11-28T10:45:30
```

## Expected Impact

1. **Reduced slippage on exits** - React within 30s instead of 5 min
2. **Better trailing stop execution** - Peak P/L updated 10x more frequently
3. **No additional LLM cost** - Price-only checks
4. **Better win preservation** - Don't let winners turn into losers

## Notes

- Fast exit monitor shares exit_rules object with main bot
- Position registration/unregistration happens in main loop
- Fast exit only executes closes, never opens positions
- Both loops can close positions - no race condition due to position state checks
