# Prompt Experimentation Guide

**Quick Reference**: How to swap prompts on the fly for testing different strategies

---

## 📋 Available Prompts

### v1_baseline_conservative
**Behavior**: Conservative, waits for clear conditions
**Use When**: Want to reduce risk, preserve capital
**File**: `llm_agent/prompts_archive/v1_baseline_conservative.txt`

### v2_aggressive_swing (CURRENT)
**Behavior**: Aggressive swing trading, daily/weekly focus, contrarian entries
**Use When**: Want more trades, capture short-term moves
**File**: `llm_agent/prompts_archive/v2_aggressive_swing.txt`

---

## 🔄 How to Swap Prompts

### Method 1: Quick Swap Script (Recommended)

```bash
# List available versions
./scripts/swap_prompt.sh

# Swap to version 1 (conservative)
./scripts/swap_prompt.sh v1_baseline_conservative

# Swap to version 2 (aggressive swing)
./scripts/swap_prompt.sh v2_aggressive_swing

# Restart bot
pkill -f llm_agent.bot_llm
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

### Method 2: Manual Edit

1. Open `llm_agent/llm/prompt_formatter.py`
2. Find lines 160-191 (the `instructions = """..."""` block)
3. Copy prompt from `llm_agent/prompts_archive/v*.txt`
4. Replace the instructions block
5. Save and restart bot

---

## 📊 Track Your Experiments

**After swapping prompts, update PROGRESS.md**:

```markdown
### Version X - Your Name (2025-10-31 HH:MM)
**Changes**: [What you changed]
**Goal**: [What you're testing]
**Bot Restarted**: PID XXXXX
**Results**: [After 24h, document what happened]
```

---

## 🆕 Create New Prompt Version

1. **Copy current prompt**:
   ```bash
   cp llm_agent/prompts_archive/v2_aggressive_swing.txt llm_agent/prompts_archive/v3_your_name.txt
   ```

2. **Edit the new file**:
   ```bash
   nano llm_agent/prompts_archive/v3_your_name.txt
   ```

3. **Swap to new version**:
   ```bash
   ./scripts/swap_prompt.sh v3_your_name
   ```

4. **Restart bot**:
   ```bash
   pkill -f llm_agent.bot_llm
   nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
   ```

5. **Document in PROGRESS.md**:
   - What you changed
   - What you expect to happen
   - Bot PID

---

## 🎯 Experiment Ideas

### More Aggressive
- Lower RSI threshold: "RSI < 30" → "RSI < 35"
- Add: "Make at least 1 trade every 3 cycles"
- Add: "Favor tokens with >100% 24h volume increase"

### More Conservative
- Higher RSI threshold: "RSI < 40" → "RSI < 35"
- Add: "Only trade when 3+ signals align"
- Add: "Prefer tokens with positive funding rate"

### Momentum Focus
- Add: "Buy into strength, not weakness"
- Change: Focus on RSI > 60, positive MACD
- Add: "Follow the trend, don't fight it"

### Mean Reversion Focus
- Add: "Buy extreme dips, sell extreme pumps"
- Change: Focus on RSI < 30 or RSI > 70
- Add: "Fade strong moves, expect reversion"

---

## 📈 Monitor Results

```bash
# View recent decisions
python3 scripts/view_decisions.py

# View detailed reasoning
python3 scripts/view_decision_details.py

# Watch live
tail -f logs/llm_bot.log | grep "LLM DECISION"
```

---

## ⏪ Revert Anytime

**Quick revert to baseline**:
```bash
./scripts/swap_prompt.sh v1_baseline_conservative
pkill -f llm_agent.bot_llm
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

**Or use git**:
```bash
git checkout llm_agent/llm/prompt_formatter.py
pkill -f llm_agent.bot_llm
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

---

## 🔍 Compare Results

After running each version for 24 hours:

1. Check decision counts:
   ```bash
   python3 scripts/view_decisions.py | grep "Action breakdown"
   ```

2. Compare BUY/SELL/NOTHING ratios
3. Check if bot is making more trades
4. Review reasoning quality

---

**Current Version**: v2_aggressive_swing (2025-10-31 14:38)
**Bot PID**: 93626
**Tracking**: See PROGRESS.md for version history
