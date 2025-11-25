# Deep42 Multi-Timeframe Rollback Guide

**Date**: 2025-11-13
**Status**: ✅ ROLLBACK MECHANISM VERIFIED

---

## Quick Rollback (30 seconds)

If you need to revert to the original single-question Deep42:

### Step 1: Edit bot_lighter.py

**File**: `lighter_agent/bot_lighter.py`
**Lines**: 430-437

**Change FROM**:
```python
# Enable Deep42 multi-timeframe context (1h regime, 4h BTC health, 6h macro)
try:
    enhanced_deep42 = self.aggregator.get_enhanced_context()
    prompt_kwargs["deep42_context"] = enhanced_deep42
    logger.info("✅ Using Deep42 multi-timeframe context (1h regime, 4h BTC, 6h macro)")
except Exception as e:
    logger.error(f"Failed to get enhanced Deep42 context: {e}")
    prompt_kwargs["deep42_context"] = None
```

**Change TO**:
```python
# Rollback: Use V1 single-question Deep42 only (via macro_context)
prompt_kwargs["deep42_context"] = None
logger.info("Using V1 single-question Deep42 (macro_context only)")
```

### Step 2: Restart Bot

```bash
# Stop current bot
pkill -f "lighter_agent.bot_lighter"

# Start with rollback (dry-run first to verify)
nohup python3 -u -m lighter_agent.bot_lighter --dry-run --interval 300 > logs/lighter_bot.log 2>&1 &

# Monitor logs
tail -f logs/lighter_bot.log
```

### Step 3: Verify Rollback

Check logs for this line:
```
Using V1 single-question Deep42 (macro_context only)
```

You should NOT see:
```
✅ Using Deep42 multi-timeframe context (1h regime, 4h BTC, 6h macro)
```

---

## What Gets Rolled Back

✅ **Disabled**:
- Multi-timeframe Deep42 queries (1h regime, 4h BTC health)
- Enhanced context dict format in prompt
- Lighter-specific profit-focused instructions tied to Deep42 usage guide

✅ **Still Active**:
- Original 6h macro_context (single Deep42 question)
- Base Lighter-specific instructions (fee-less, volume focus)
- All other bot functionality unchanged

---

## Re-Enable Multi-Timeframe (If Needed Later)

Simply reverse the change in Step 1:

```python
# Enable Deep42 multi-timeframe context (1h regime, 4h BTC health, 6h macro)
try:
    enhanced_deep42 = self.aggregator.get_enhanced_context()
    prompt_kwargs["deep42_context"] = enhanced_deep42
    logger.info("✅ Using Deep42 multi-timeframe context (1h regime, 4h BTC, 6h macro)")
except Exception as e:
    logger.error(f"Failed to get enhanced Deep42 context: {e}")
    prompt_kwargs["deep42_context"] = None
```

Then restart bot.

---

## Files Affected by Implementation

Only these 3 files were modified:

1. **`llm_agent/data/macro_fetcher.py`** - Added multi-timeframe methods
   - `get_regime_context()` - 1h caching
   - `get_btc_health()` - 4h caching
   - `get_enhanced_context()` - Combines all three
   - Rollback: These methods remain but won't be called

2. **`llm_agent/llm/prompt_formatter.py`** - Enhanced Deep42 handling
   - Lines 231-266: Dict format handling
   - Lines 355-500: Lighter-specific instructions
   - Rollback: Falls back to string format automatically (backward compatible)

3. **`lighter_agent/bot_lighter.py`** - Enable enhanced context
   - Lines 423-437: DEX name, analyzed_tokens, enhanced_deep42
   - Rollback: Single line change as shown above

---

## Cost Savings from Rollback

**Before Rollback** (Multi-timeframe):
- Macro (6h): 4 calls/day
- Regime (1h): 24 calls/day
- BTC Health (4h): 6 calls/day
- **Total**: 34 Deep42 calls/day (~$1.70/day)

**After Rollback** (V1 original):
- Macro (6h): 4 calls/day
- **Total**: 4 Deep42 calls/day (~$0.20/day)

**Savings**: $1.50/day ($45/month)

---

## When to Use Rollback

**Consider rollback if**:
- Bot making poor quality decisions with multi-timeframe context
- Deep42 API experiencing high latency (>10 seconds per call)
- Cost concerns ($1.70/day vs $0.20/day)
- Need to simplify debugging during testing

**Keep multi-timeframe if**:
- Bot successfully avoiding pump-and-dump traps (quality score < 5)
- Win rate improving with regime-aware decisions
- Risk-off filtering reducing catastrophic losses (-10%+)
- Cost justified by improved performance

---

## Verification Checklist

After rollback, verify:

- [ ] Log shows "Using V1 single-question Deep42 (macro_context only)"
- [ ] No log lines about "multi-timeframe context"
- [ ] Prompt still contains macro_context section
- [ ] Prompt does NOT contain "DEEP42 MARKET INTELLIGENCE (Multi-Timeframe)" header
- [ ] Bot making decisions normally
- [ ] No errors in logs

---

## Support

If rollback doesn't work:
1. Check git diff: `git diff lighter_agent/bot_lighter.py`
2. Verify only lines 430-437 changed
3. Check Python syntax (no typos in the simple change)
4. Review logs for any Python errors on bot start

**File**: `research/DEEP42_ROLLBACK_GUIDE.md`
**Test Date**: 2025-11-13
**Status**: ✅ Verified working
