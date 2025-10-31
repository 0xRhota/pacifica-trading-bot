# Prompt Version Archive

**Purpose**: Store all prompt versions for easy swapping/testing

---

## Quick Start

**List versions**:
```bash
./scripts/swap_prompt.sh
```

**Swap to a version**:
```bash
./scripts/swap_prompt.sh v1_baseline_conservative
```

**Then restart bot**:
```bash
pkill -f llm_agent.bot_llm
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

---

## Version History

### v1_baseline_conservative
- **Date**: 2025-10-30
- **Behavior**: Conservative, waits for clear conditions
- **NOTHING trigger**: "if conditions unclear or strategy suggests waiting"
- **Strategy guidance**: None (generic)

### v2_aggressive_swing
- **Date**: 2025-10-31
- **Behavior**: Aggressive swing trading, daily/weekly focus
- **NOTHING trigger**: "ONLY if extremely uncertain - prefer action over inaction"
- **Strategy guidance**:
  - Focus on daily/weekly movements
  - Look for 24h volume spikes >50%
  - Contrarian entries (Fear < 30, RSI < 40)
  - Profit taking (Fear > 70, RSI > 70)
  - "Don't wait for perfect setups"

---

## Creating New Versions

1. Copy existing version:
   ```bash
   cp v2_aggressive_swing.txt v3_your_experiment.txt
   ```

2. Edit the new file:
   ```bash
   nano v3_your_experiment.txt
   ```

3. Document in `PROGRESS.md` what you changed and why

4. Swap and test:
   ```bash
   ./scripts/swap_prompt.sh v3_your_experiment
   ```

---

See `PROMPT_EXPERIMENTS.md` for full guide
