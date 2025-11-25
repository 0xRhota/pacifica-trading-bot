# Prompt Versioning & Logging Strategy

**Date**: 2025-11-06
**Purpose**: Document versioning convention and logging approach for prompt experiments

---

## Versioning Convention

### Current Approach: Descriptive Names ✅

**Format**: `v{number}_{description}`

**Examples**:
- `v1_original` - Original prompt with Deep42 macro context
- `v2_deep_reasoning` - Enhanced prompt with mandatory exact citations
- `v3_longer_holds` - Future: Optimized for longer hold times

**Pros**:
- Self-documenting (immediately know what each version does)
- Easy to remember (`v2_deep_reasoning` vs `v2.1` - which is which?)
- grep-friendly in logs

**Cons**:
- Slightly longer names
- Need naming convention consistency

### Alternative: Semantic Versioning

**Format**: `v{major}.{minor}.{patch}`

**Examples**:
- `v1.0` - Original prompt
- `v2.0` - Major prompt redesign (Deep Reasoning)
- `v2.1` - Minor tweaks to V2
- `v2.1.1` - Bugfix to V2.1

**When to use**:
- If iterating rapidly on same version (v2.0 → v2.1 → v2.2)
- If need strict compatibility tracking

**AVOID**:
- ❌ `v.01` or `v.1` (non-standard, confusing)
- ❌ `v01` or `v02` (looks like dates)

### Recommendation for This Project

**Use descriptive names** (`v1_original`, `v2_deep_reasoning`) because:
1. We're testing fundamentally different approaches (not iterating)
2. Logs are more readable
3. Easy to understand what's running without docs

If we start iterating on V2 (v2.1, v2.2, etc.), consider:
- `v2_deep_reasoning_improved`
- `v2_deep_reasoning_faster`
- Or switch to semantic: `v2.1`, `v2.2`

---

## Logging Strategy

### Current Approach: Single Log File with Clear Markers ✅

**File**: `logs/lighter_bot.log`

**Markers**:
```
================================================================================
Decision Cycle - 2025-11-06 22:03:48 | V2 (Deep Reasoning)
================================================================================

[... market data ...]

================================================================================
🤖 LLM DECISIONS (1 total)
📋 Prompt Version: v2_deep_reasoning
✨ Using V2: Deep Reasoning + Exact Citations + No Deep42
================================================================================
```

**Benefits**:
- ✅ Easy to compare V1 vs V2 in same log
- ✅ Clear version markers for filtering
- ✅ Standard approach (one log per bot)
- ✅ grep-friendly: `grep "V2 (Deep Reasoning)" logs/lighter_bot.log`

**How to filter logs**:
```bash
# Show only V2 decision cycles
grep "V2 (Deep Reasoning)" logs/lighter_bot.log

# Show only V1 decision cycles
grep "V1 (Original)" logs/lighter_bot.log

# Show all decisions with version
grep -A 5 "LLM DECISIONS" logs/lighter_bot.log | grep -E "Prompt Version|Using V"

# Compare V1 vs V2 reasoning
grep -A 20 "REASON:" logs/lighter_bot.log | grep -B 2 "V2\|V1"
```

### Alternative: Separate Log Files

**Setup**:
```python
# In bot initialization
prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
if prompt_version == "v2_deep_reasoning":
    log_file = "logs/lighter_bot_v2.log"
else:
    log_file = "logs/lighter_bot_v1.log"
```

**Pros**:
- Clean separation
- Smaller files

**Cons**:
- ❌ Harder to compare V1 vs V2 side-by-side
- ❌ Need to track which file is active
- ❌ More complex log rotation

**Recommendation**: Stick with single log + clear markers

---

## Log Markers Reference

### At Startup

```
✅ Lighter Trading Bot initialized successfully
📝 Active Prompt Version: v2_deep_reasoning
```

### At Decision Cycle Start

```
================================================================================
Decision Cycle - 2025-11-06 22:03:48 | V2 (Deep Reasoning)
================================================================================
```

### At LLM Decision Output

```
================================================================================
🤖 LLM DECISIONS (1 total)
📋 Prompt Version: v2_deep_reasoning
✨ Using V2: Deep Reasoning + Exact Citations + No Deep42
================================================================================
```

### In Decision Details

```
[Decision 1/1]
  Symbol: TRUMP
  Action: BUY
  Confidence: 0.78
  Reason: RSI 34 (approaching oversold), MACD -0.0 histogram...
```

---

## Comparing V1 vs V2 in Logs

### Quick Comparison Script

```bash
#!/bin/bash
# compare_versions.sh

echo "=== V1 DECISIONS (last 10) ==="
grep -B 2 "V1 (Original)" logs/lighter_bot.log | tail -30

echo ""
echo "=== V2 DECISIONS (last 10) ==="
grep -B 2 "V2 (Deep Reasoning)" logs/lighter_bot.log | tail -30

echo ""
echo "=== V1 REASONING QUALITY ==="
grep -A 5 "V1 (Original)" logs/lighter_bot.log | grep "REASON:" | tail -5

echo ""
echo "=== V2 REASONING QUALITY ==="
grep -A 5 "V2 (Deep Reasoning)" logs/lighter_bot.log | grep "REASON:" | tail -5
```

### Metric Extraction

**Count invalid symbols**:
```bash
# V1
grep "V1 (Original)" logs/lighter_bot.log | wc -l  # Total V1 cycles
grep -A 20 "V1 (Original)" logs/lighter_bot.log | grep "REJECTED: Symbol" | wc -l

# V2
grep "V2 (Deep Reasoning)" logs/lighter_bot.log | wc -l  # Total V2 cycles
grep -A 20 "V2 (Deep Reasoning)" logs/lighter_bot.log | grep "REJECTED: Symbol" | wc -l
```

**Check for "likely" statements** (vague reasoning):
```bash
# V1
grep -A 20 "V1 (Original)" logs/lighter_bot.log | grep -i "likely" | wc -l

# V2
grep -A 20 "V2 (Deep Reasoning)" logs/lighter_bot.log | grep -i "likely" | wc -l
```

---

## Version Switch Checklist

When switching from V1 to V2 (or vice versa):

1. ✅ Edit `llm_agent/config_prompts.py` line 20
2. ✅ Restart bot
3. ✅ Check first log entry for version confirmation
4. ✅ Monitor first 2-3 decision cycles for quality
5. ✅ Compare reasoning quality to baseline

**Quick switch commands**:
```bash
# Switch to V2
nano llm_agent/config_prompts.py  # Change line 20 to v2_deep_reasoning
pkill -f lighter_agent.bot_lighter
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# Verify V2 loaded
tail -20 logs/lighter_bot.log | grep "Active Prompt Version"

# Watch V2 decisions
tail -f logs/lighter_bot.log | grep -E "Decision Cycle|V2 \(Deep Reasoning\)|LLM DECISIONS"
```

---

## Future Versioning Ideas

### If Adding More Versions

- `v3_macro_sensitive` - Re-add macro context but with better integration
- `v4_risk_adjusted` - Dynamic position sizing based on market conditions
- `v5_ml_hybrid` - Combine LLM reasoning with ML predictions

### If Iterating on V2

Option A: Descriptive suffixes
- `v2_deep_reasoning_fast` - Optimized for speed
- `v2_deep_reasoning_conservative` - Lower risk thresholds

Option B: Semantic versioning
- `v2.0` - Current V2
- `v2.1` - Minor improvements (better exit logic)
- `v2.2` - Added stochastic explicit values

---

## Key Takeaways

1. **Use descriptive version names** for major changes (`v1_original`, `v2_deep_reasoning`)
2. **Single log file** with clear markers is best for comparison
3. **Version visible in**:
   - Startup logs
   - Decision cycle header
   - LLM decisions section
4. **Easy grep filtering** for analysis
5. **One-line config change** to switch versions

This makes A/B testing and performance analysis straightforward.
