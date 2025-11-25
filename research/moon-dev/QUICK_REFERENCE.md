# RBI Agent - Quick Reference

**Purpose**: Automated strategy discovery and backtesting  
**Status**: MVP Complete ✅  
**Location**: `rbi_agent/`

---

## Quick Start

```bash
# Test a simple strategy
python -m rbi_agent.rbi_agent \
    --strategy "Buy when RSI < 30" \
    --symbols SOL ETH BTC \
    --days 30
```

---

## What It Does

1. **Takes Strategy Description** (natural language)
   - Example: "Buy when RSI < 30 and volume increases 30%"

2. **LLM Generates Backtest Code**
   - Converts description to Python function
   - Uses DeepSeek API

3. **Tests on Historical Data**
   - Fetches last N days from Pacifica API
   - Executes strategy on each candle
   - Calculates performance metrics

4. **Returns Pass/Fail**
   - Default thresholds: Return > 1%, Win Rate > 40%, Sharpe > 0.5

---

## Files

- `rbi_agent.py` - Main implementation
- `README.md` - Full documentation
- `EXAMPLES.md` - Usage examples

---

## Dependencies

**Read-Only Access To**:
- `llm_agent/data/pacifica_fetcher.py` - Historical data
- `llm_agent/data/indicator_calculator.py` - Indicators
- `llm_agent/llm/model_client.py` - LLM client

**Does NOT Modify**:
- Any live bot code
- Any configuration files
- Any prompts

---

## Example Output

```
✅ Strategy PASSED
Return: 3.2%
Win Rate: 45.0%
Sharpe Ratio: 0.8
Total Trades: 12
```

---

## Integration Options

1. **Manual Review** (Current)
   - Run RBI agent manually
   - Review results
   - Manually add to prompt

2. **Auto-Discovery** (Future)
   - Weekly automated runs
   - Save passing strategies
   - Bot references proven strategies

---

**See `README.md` for full documentation**

