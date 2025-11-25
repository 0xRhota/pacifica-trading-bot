# Morning V2 Deployment Checklist

**Quick Reference** - Everything you need in one place

---

## 🎯 Quick Deploy (One Command)

```bash
pkill -f "lighter_agent.bot_lighter" && sleep 3 && nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 & sleep 5 && ./monitor_v2.sh
```

This will:
1. Stop current bot
2. Wait for graceful shutdown
3. Start V2 (config already set to v2_deep_reasoning)
4. Launch monitoring script

---

## 📊 Monitor V2 Live

```bash
./monitor_v2.sh
```

Or manually:
```bash
tail -f logs/lighter_bot.log | grep -E "Decision Cycle.*V2|LLM DECISIONS|V2 \(Deep|Order placed|FILLED" --line-buffered --color=always
```

---

## ✅ What V2 Changed

### Quality Improvements
- ✅ **Exact citations**: "RSI 34.2" instead of "RSI likely low"
- ✅ **No invalid symbols**: 0 vs V1's ~3 per cycle
- ✅ **Structured reasoning**: STEP 1-4 format
- ✅ **No Deep42**: Removed macro context (too slow/general for 5min scalping)

### What V2 Didn't Change
- Position sizing still ~$10 (will improve next)
- Same 5-minute decision cycle
- Same Lighter markets (101 pairs)
- Same risk management (stop loss/take profit)

---

## 🔍 First Cycle Check (5 minutes after deploy)

Look for these in logs:

```
✅ "📝 Active Prompt Version: v2_deep_reasoning"
✅ "Decision Cycle - ... | V2 (Deep Reasoning)"
✅ "✨ Using V2: Deep Reasoning + Exact Citations + No Deep42"
```

---

## 🚨 If Something Looks Wrong

### Rollback to V1 (30 seconds)

```bash
# 1. Stop bot
pkill -f "lighter_agent.bot_lighter"

# 2. Edit config (change line 20)
nano llm_agent/config_prompts.py
# Change: ACTIVE_PROMPT_VERSION = "v1_original"

# 3. Restart
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

---

## 📈 After V2 is Stable (Next Steps)

1. **Intelligent Position Sizing** (already designed):
   - Multi-factor sizing: confidence × momentum × volatility × quality × streak
   - Dynamic range: $10-$30 (vs current fixed $10)
   - Aggressive preset for your $100 account risk tolerance
   - Files ready: `lighter_agent/execution/position_sizing.py`, `config/position_sizing_config.py`

2. **Compare V1 vs V2 Performance**:
   - Invalid symbol rate
   - Reasoning quality (citations vs vague statements)
   - Win rate (does better reasoning = better trades?)
   - Volume executed

---

## 📝 Files Created for You

- `DEPLOY_V2_MORNING.md` - Complete deployment guide with troubleshooting
- `monitor_v2.sh` - Easy log monitoring script (just run `./monitor_v2.sh`)
- `research/V2_TEST_RESULTS.md` - Test results showing V2 improvements
- `research/VERSIONING_AND_LOGGING.md` - Versioning strategy docs
- `research/INTELLIGENT_POSITION_SIZING.md` - Position sizing design (for next phase)

---

## 🎯 Current State

- ✅ V2 prompt built and tested
- ✅ Config set to v2_deep_reasoning
- ✅ Logging enhanced with version markers
- ✅ All integration bugs fixed
- ✅ Monitoring script ready
- ✅ Position sizing designed (not yet integrated)
- 🟡 Live bot running overnight (DO NOT INTERRUPT)

---

**When you wake up**: Run the one-command deploy above, monitor first cycle, enjoy V2! 🚀

**If you want more aggressive position sizing**: After V2 is stable, we'll integrate the intelligent sizing system with an "aggressive" preset for your $100 account.
