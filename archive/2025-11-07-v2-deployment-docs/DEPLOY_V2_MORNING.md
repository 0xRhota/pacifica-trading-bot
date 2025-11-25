# V2 Deep Reasoning Deployment Guide

**Date Prepared**: 2025-11-06
**Status**: Ready to deploy - DO NOT INTERRUPT CURRENT BOT

---

## ✅ What's Already Done

1. **V2 Prompt Built & Tested**:
   - File: `llm_agent/llm/prompt_formatter_v2_deep_reasoning.py`
   - Features: Exact citations, no Deep42, chain-of-thought reasoning
   - Test Results: A-/B+ grade (0 invalid symbols, 95% exact citations)

2. **Config Set to V2**:
   - File: `llm_agent/config_prompts.py` line 20
   - Setting: `ACTIVE_PROMPT_VERSION = "v2_deep_reasoning"`
   - ✅ Already configured - will activate on restart

3. **Logging Enhanced**:
   - File: `lighter_agent/bot_lighter.py` lines 190-194, 493-501
   - Features: Clear V2/V1 version markers in logs
   - Grep-friendly for filtering

4. **Integration Fixed**:
   - Conditional macro context fetching (V2 doesn't need Deep42)
   - Conditional parameter passing to prompt formatters
   - All bugs from testing resolved

---

## 🚀 Morning Deployment Steps

### Step 1: Check Current Bot Status

```bash
# Check if bot is running
pgrep -f "lighter_agent.bot_lighter"

# If running, check latest activity
tail -100 logs/lighter_bot.log | grep -E "Decision Cycle|Order placed|FILLED"
```

### Step 2: Backup Current Log

```bash
# Archive V1 log for comparison
cp logs/lighter_bot.log logs/lighter_bot_V1_backup_$(date +%Y%m%d_%H%M%S).log
```

### Step 3: Deploy V2

```bash
# Stop current bot
pkill -f "lighter_agent.bot_lighter"

# Wait for graceful shutdown
sleep 3

# Start V2 (config already set)
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# Get new PID
pgrep -f "lighter_agent.bot_lighter"
```

### Step 4: Verify V2 is Active

```bash
# Wait for first log entry
sleep 10

# Check version in logs
tail -30 logs/lighter_bot.log | grep -E "Active Prompt Version|V2 \\(Deep Reasoning\\)"

# Should see:
# ✅ "📝 Active Prompt Version: v2_deep_reasoning"
# ✅ "Decision Cycle - ... | V2 (Deep Reasoning)"
```

### Step 5: Monitor First Decision Cycle (5 minutes)

Use the new monitoring script:
```bash
./monitor_v2.sh
```

Or manually:
```bash
tail -f logs/lighter_bot.log | grep -E "Decision Cycle|LLM DECISIONS|V2|Executing decision|Order placed|FILLED" --line-buffered --color=always
```

---

## 📊 What to Look For in V2 Logs

### Version Markers (Should Appear Every Cycle)

```
================================================================================
Decision Cycle - 2025-11-06 22:03:48 | V2 (Deep Reasoning)
================================================================================
```

```
================================================================================
🤖 LLM DECISIONS (1 total)
📋 Prompt Version: v2_deep_reasoning
✨ Using V2: Deep Reasoning + Exact Citations + No Deep42
================================================================================
```

### V2 Quality Indicators

✅ **Exact citations**: "RSI 34.2 (approaching oversold)" not "RSI likely low"
✅ **Valid symbols only**: BTC, SOL, ETH, DOGE, etc. (from Lighter's 101 markets)
✅ **Structured reasoning**: STEP 1-4 format visible in reasoning
✅ **No vague statements**: No "likely", "probably", "seems" without data

### Example V2 Decision Format

```
[Decision 1/1]
  Symbol: DOGE
  Action: BUY
  Confidence: 0.78
  Reason: STEP 1: RSI 34.2 on 5m approaching oversold (typical reversal zone <30).
  STEP 2: MACD histogram -0.0142 flattening suggests weakening downward momentum.
  STEP 3: Stochastic K 28.3 in oversold territory (<30) indicates potential bounce.
  STEP 4: Pattern aligns with oversold reversal setup. Entering small long position.
```

---

## 🔄 Rollback to V1 (If Needed)

If V2 has issues, quick rollback:

```bash
# 1. Stop bot
pkill -f "lighter_agent.bot_lighter"

# 2. Switch config back to V1
# Edit llm_agent/config_prompts.py line 20:
nano llm_agent/config_prompts.py
# Change: ACTIVE_PROMPT_VERSION = "v1_original"

# 3. Restart with V1
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

---

## 📈 Comparing V1 vs V2 Performance

### Filter V1 Decisions (from backup log)

```bash
grep -A 20 "V1 (Original)" logs/lighter_bot_V1_backup*.log | grep -E "Symbol|Action|Confidence|Reason" | less
```

### Filter V2 Decisions (from new log)

```bash
grep -A 20 "V2 (Deep Reasoning)" logs/lighter_bot.log | grep -E "Symbol|Action|Confidence|Reason" | less
```

### Compare Invalid Symbol Rate

```bash
# V1 invalid symbols
grep "REJECTED: Symbol" logs/lighter_bot_V1_backup*.log | wc -l

# V2 invalid symbols (should be 0 or very low)
grep "REJECTED: Symbol" logs/lighter_bot.log | wc -l
```

### Compare Reasoning Quality

```bash
# V1 vague statements ("likely", "probably")
grep -A 5 "Reason:" logs/lighter_bot_V1_backup*.log | grep -i "likely\|probably" | wc -l

# V2 vague statements (should be much lower)
grep -A 5 "Reason:" logs/lighter_bot.log | grep -i "likely\|probably" | wc -l
```

---

## ⚠️ Known Limitations (Future Work)

1. **Position Sizing**: Still using confidence-based sizing (~$10 per position)
   - V2 doesn't change position sizing yet
   - Intelligent position sizing designed but not integrated
   - Will work on more dynamic/aggressive sizing after V2 is stable

2. **Log Tailing Issue**: User reported `tail -f logs/lighter_bot.log` not working
   - May be buffering issue
   - Use monitoring script instead (see below)

---

## 🛠️ Troubleshooting

### Issue: Bot won't start

```bash
# Check for errors in last run
tail -100 logs/lighter_bot.log | grep -i "error\|exception\|failed"

# Check if port/API issues
python3 -c "from lighter_agent.bot_lighter import LighterTradingBot; bot = LighterTradingBot(live_mode=False); print('✅ Bot initialized OK')"
```

### Issue: V2 not loading

```bash
# Verify config
python3 -c "from llm_agent.config_prompts import ACTIVE_PROMPT_VERSION, get_prompt_formatter; print(f'Active: {ACTIVE_PROMPT_VERSION}'); print(f'Formatter: {type(get_prompt_formatter()).__name__}')"

# Should output:
# Active: v2_deep_reasoning
# Formatter: PromptFormatterV2
```

### Issue: Can't see logs in real-time

Try the monitoring script (see below) or:
```bash
# Alternative to tail -f
watch -n 2 'tail -50 logs/lighter_bot.log'

# Or with grep
watch -n 2 'tail -100 logs/lighter_bot.log | grep -E "Decision Cycle|LLM DECISIONS|V2"'
```

---

## 📝 Test Results Reference

From dry-run testing (see `research/V2_TEST_RESULTS.md`):

| Metric | V1 Baseline | V2 Deep Reasoning |
|--------|-------------|-------------------|
| **Invalid Symbols** | ~3 per cycle | 0 per cycle ✅ |
| **Exact RSI Citations** | ~40% | ~95% ✅ |
| **"Likely" Statements** | ~60% | ~5% ✅ |
| **Reasoning Quality** | C+ | A-/B+ ✅ |

**Verdict**: V2 significantly improves decision quality and reasoning precision.

---

## ✅ Ready to Deploy

Everything is prepared. Just run Step 3 when ready in the morning.

**One command deployment**:
```bash
pkill -f "lighter_agent.bot_lighter" && sleep 3 && nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 & sleep 5 && tail -30 logs/lighter_bot.log | grep -E "Active Prompt Version|V2"
```

Good luck! 🚀
