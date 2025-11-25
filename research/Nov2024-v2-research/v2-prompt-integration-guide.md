# V2 Deep Reasoning Prompt - Integration Guide

**Created**: 2025-11-06
**Status**: Ready to test
**Rollback**: One-line config change

---

## 📦 What Was Created

### 1. New Prompt Formatter
**File**: `llm_agent/llm/prompt_formatter_v2_deep_reasoning.py`

**Key Improvements**:
- ❌ **Removes Deep42 macro context** (eliminates invalid symbol suggestions like FOMO, RDNT)
- ✅ **Enforces chain-of-thought** analysis (Step 1: 5-min indicators → Step 2: 4h context → Step 3: confluence → Step 4: scalping suitability)
- ✅ **Mandatory exact citations** (no "likely oversold" - must cite actual RSI value)
- ✅ **Symbol validation** (explicit reminder to only use available markets)
- ✅ **5-minute scalping focus** (removes long-term narrative noise)

### 2. Config Switch System
**File**: `llm_agent/config_prompts.py`

**Easy switching**:
```python
# Change this one line to switch strategies:
ACTIVE_PROMPT_VERSION = "v1_original"  # Current (with Deep42)
ACTIVE_PROMPT_VERSION = "v2_deep_reasoning"  # New (no Deep42, strict citations)
```

### 3. Analysis Documentation
**File**: `research/reasoning-quality-analysis.md`

Complete analysis with examples, root causes, and expected improvements.

---

## 🎯 Expected Improvements

| Metric | V1 (Current) | V2 (Expected) | Improvement |
|--------|--------------|---------------|-------------|
| Invalid symbols per cycle | ~3 (FOMO, RDNT, etc.) | 0 | 100% |
| Indicator specificity | ~40% cite exact values | ~85% cite exact values | +113% |
| "Likely" statements | ~60% of decisions | <5% of decisions | -92% |
| Reasoning quality grade | C+ average | B+ average | +1 letter grade |
| Generic exits | ~50% say "better opportunities" | <10% generic | -80% |

---

## 🚀 How to Test V2

### Option A: Quick Test (No Code Changes)

**1. Enable V2**:
```bash
# Edit llm_agent/config_prompts.py line 16:
ACTIVE_PROMPT_VERSION = "v2_deep_reasoning"
```

**2. Test in dry-run mode first**:
```bash
# Stop live bot
pkill -f "lighter_agent.bot_lighter"

# Run ONE dry-run cycle
python3 -m lighter_agent.bot_lighter --dry-run --interval 300
```

**3. Compare reasoning quality**:
```bash
# Look for [V2 PROMPT] markers in output
# Check if decisions cite exact RSI/MACD/Stochastic values
# Verify no invalid symbols suggested
```

**4. If good, deploy to live**:
```bash
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

### Option B: Side-by-Side Comparison

**1. Save current logs**:
```bash
cp logs/lighter_bot.log logs/v1_baseline_decisions.log
```

**2. Run V1 for 3 cycles** (15 min):
```bash
tail -f logs/lighter_bot.log | grep -A 5 "REASON:"
# Document quality
```

**3. Switch to V2** and run 3 cycles:
```bash
# Edit config_prompts.py to v2_deep_reasoning
# Restart bot
tail -f logs/lighter_bot.log | grep -A 5 "REASON:"
# Compare quality
```

**4. Compare metrics**:
- Count "likely" statements (should drop to near zero)
- Count invalid symbol rejections (should drop to zero)
- Check indicator citation completeness

---

## 🔄 How to Rollback

### If V2 has issues:

**1. Stop bot**:
```bash
pkill -f "lighter_agent.bot_lighter"
```

**2. Rollback config** (ONE LINE CHANGE):
```bash
# Edit llm_agent/config_prompts.py line 16:
ACTIVE_PROMPT_VERSION = "v1_original"
```

**3. Restart**:
```bash
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

**Done!** Back to original behavior in 30 seconds.

---

## 📊 Position Sizing Explained

### Current Logic (Confidence-Based)

**Location**: `lighter_agent/execution/lighter_executor.py:239-244`

```python
if confidence >= 0.8:
    position_size_usd = self.default_position_size * 2.0  # $10
elif confidence >= 0.6:
    position_size_usd = self.default_position_size * 1.5  # $7.50
else:
    position_size_usd = self.default_position_size  # $5
```

**Default position size**: `$5` (set in `bot_lighter.py:62`)

### Why Most Trades Are $10

Your bot is giving **0.8+ confidence** on most trades, triggering the 2x multiplier:

```
Confidence 0.82 → $5 * 2.0 = $10
Confidence 0.75 → $5 * 1.5 = $7.50
Confidence 0.65 → $5 * 1.5 = $7.50
Confidence 0.55 → $5 * 1.0 = $5
```

### Is This Hardcoded?

**Sort of**. The multipliers (2.0x, 1.5x, 1.0x) are hardcoded, but based on confidence scores from the LLM.

**To change**:
1. **Adjust default**: Change `position_size: float = 5.0` in `bot_lighter.py:62`
2. **Adjust multipliers**: Edit the confidence thresholds in `lighter_executor.py:239-244`
3. **Flat sizing**: Remove confidence-based logic entirely

### Recommendation

Leave as-is for now. The confidence-based sizing is actually smart:
- High confidence (good setups) → bigger size
- Low confidence (marginal setups) → smaller size

V2 prompt might produce MORE ACCURATE confidence scores (better calibration), which could naturally improve position sizing.

---

## 🔍 How to Monitor V2 Performance

### Key Log Markers

**V2 is active when you see**:
```
[V2 PROMPT] Formatted prompt: 12450 characters (~3112 tokens)
[V2 PROMPT] Deep42 macro context: DISABLED (5-min scalping focus)
[V2 PROMPT] Reasoning mode: MANDATORY exact citations + chain-of-thought
```

### Quality Checks

**1. Indicator Specificity** (should be ~85%):
```bash
tail -200 logs/lighter_bot.log | grep "REASON:" | wc -l  # Total decisions
tail -200 logs/lighter_bot.log | grep "REASON:.*RSI [0-9]" | wc -l  # Cite exact RSI
# Divide: Should be 85%+
```

**2. Invalid Symbols** (should be 0):
```bash
tail -200 logs/lighter_bot.log | grep "REJECTED.*is not a Lighter market" | wc -l
# Should be: 0
```

**3. "Likely" Statements** (should be <5%):
```bash
tail -200 logs/lighter_bot.log | grep "REASON:.*likely" | wc -l
# Should be: 0-2 max
```

### Performance Metrics

**1. Decision latency**:
```bash
# Check timestamp gaps between "Decision Cycle" entries
# V1: ~5-8 seconds
# V2: Might be 8-12 seconds (acceptable if quality improves)
```

**2. Token usage**:
```bash
tail -100 logs/lighter_bot.log | grep "tokens:"
# V1: ~5000-6000 tokens per decision
# V2: ~6500-8000 tokens (stricter prompts = longer)
```

**3. Decision acceptance rate**:
```bash
# Count ACCEPTED vs REJECTED
tail -200 logs/lighter_bot.log | grep -E "ACCEPTED|REJECTED" | grep -c ACCEPTED
tail -200 logs/lighter_bot.log | grep -E "ACCEPTED|REJECTED" | grep -c REJECTED
# V2 should have higher acceptance rate (fewer invalid symbols)
```

---

## ⚠️ Rollback Triggers

**Immediately rollback to V1 if**:
1. Decision cycles take >15 seconds consistently
2. LLM errors increase >2x
3. Cost per decision >$0.002 (2x current)
4. Bot suggests NO decisions for 3+ consecutive cycles
5. Any unexpected exceptions in prompt formatting

**Consider rolling back if**:
1. Reasoning becomes TOO verbose (harder to debug)
2. No improvement in invalid symbol rate (still suggesting FOMO/RDNT)
3. Indicator specificity doesn't improve
4. Confidence scores become miscalibrated

---

## 📈 Success Criteria

### V2 is successful if:

**Must Have** (75% threshold):
- ✅ Zero invalid symbol suggestions (FOMO, RDNT, etc.)
- ✅ 80%+ decisions cite exact RSI values
- ✅ <5% "likely" statements
- ✅ No increase in decision errors

**Nice to Have** (bonus points):
- ✅ Better confidence calibration (0.8+ only on truly strong setups)
- ✅ More specific exit reasons (not just "better opportunities")
- ✅ Better P&L outcomes (prove quality → profit)

### Evaluation Timeline

- **15 min** (3 cycles): Check for obvious issues
- **1 hour** (12 cycles): Verify indicator citation improvement
- **4 hours** (48 cycles): Compare P&L vs historical baseline
- **24 hours**: Make final keep/rollback decision

---

## 🛠️ Troubleshooting

### "Module not found: llm_agent.config_prompts"
```bash
# Make sure file exists
ls -la llm_agent/config_prompts.py

# Restart Python to reload imports
pkill -f bot_lighter && sleep 2 && nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

### "No decisions for 3 cycles"
Prompt might be TOO strict. Check logs for:
```bash
tail -100 logs/lighter_bot.log | grep -i "error\|exception"
```
If LLM is erroring, rollback to V1.

### "Still suggesting FOMO/RDNT"
V2 failed. Possible causes:
1. DeepSeek ignoring instructions (try Claude Sonnet)
2. Prompt still has Deep42 context (verify V2 loaded)
3. Symbol validation not working

Check which formatter loaded:
```bash
tail -50 logs/lighter_bot.log | grep "ACTIVE PROMPT"
# Should say: v2_deep_reasoning
```

---

## 📝 Next Steps

**Immediate** (tonight):
1. ✅ Files created and documented
2. ⏳ Test V2 in dry-run mode (1 cycle)
3. ⏳ Compare reasoning quality vs V1
4. ⏳ Deploy to live if quality improved

**Tomorrow**:
1. ⏳ Monitor V2 for 12 cycles (1 hour)
2. ⏳ Measure key metrics (invalid symbols, specificity, "likely")
3. ⏳ Decide: keep V2, rollback, or iterate

**This Week**:
1. ⏳ A/B test models: DeepSeek vs Claude Sonnet 3.5
2. ⏳ Optimize cost/quality tradeoff
3. ⏳ Document final configuration

---

## 🎯 Quick Commands Reference

```bash
# TEST V2 (dry-run)
python3 -m lighter_agent.bot_lighter --dry-run --interval 300

# DEPLOY V2 (live)
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# MONITOR V2
tail -f logs/lighter_bot.log | grep -E "V2 PROMPT|REASON:|REJECTED"

# CHECK QUALITY
tail -200 logs/lighter_bot.log | grep "REASON:" | head -10

# ROLLBACK TO V1
# 1. Edit llm_agent/config_prompts.py → ACTIVE_PROMPT_VERSION = "v1_original"
# 2. pkill -f bot_lighter
# 3. Restart bot
```

---

**Ready to test!** 🚀

All files organized, rollback is one line, monitoring is clear.
