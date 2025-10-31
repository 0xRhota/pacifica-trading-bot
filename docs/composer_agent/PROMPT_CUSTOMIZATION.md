# Prompt Customization Guide

**Quick Reference**: How to adjust your LLM trading bot's behavior

---

## Current Prompt System

**Location**: `llm_agent/llm/prompt_formatter.py` (lines 160-182)

**Problem**: Prompt is hardcoded in Python string - requires code changes to modify.

---

## How Prompt Works Now

### Prompt Structure

The prompt sent to DeepSeek LLM consists of:

1. **Custom Deep42 Context** (if generated)
   - LLM-generated question about market
   - Deep42's answer

2. **Token Deep Dives** (3 tokens selected by LLM)
   - Deep42 analysis for selected tokens

3. **Position Evaluations** (if positions exist)
   - Deep42 evaluation of open positions

4. **Macro Context** (cached 12h)
   - Fear & Greed Index
   - CoinGecko metrics
   - Deep42 market analysis

5. **Market Data Table** (all 28 markets)
   - Price, volume, funding, OI, RSI, MACD, SMA

6. **Open Positions** (if any)

7. **Instructions** ← **THIS IS WHAT YOU WANT TO CHANGE**
   - Current instructions are conservative
   - Tells LLM to wait if conditions unclear

### Current Instructions (Lines 160-182)

```python
instructions = """Instructions:
- Consider the macro context (overall market state, catalysts, outlook)
- Analyze current market data (price, volume, funding, OI, indicators)
- Review open positions (if any) and decide if you should CLOSE them or let them run
- Make ONE decision: BUY <SYMBOL>, SELL <SYMBOL>, CLOSE <SYMBOL>, or NOTHING
- Explain your reasoning citing SPECIFIC data sources (e.g., "Deep42 analysis shows...", "Fear & Greed index at X...", "SOL RSI at Y...", "Funding rate at Z...")

Decision Options:
- BUY <SYMBOL>: Enter new long position (only if room for more positions)
- SELL <SYMBOL>: Enter new short position (only if room for more positions)
- CLOSE <SYMBOL>: Close existing position (if it's time to exit based on your analysis)
- NOTHING: No action (if conditions unclear or strategy suggests waiting)

You have FULL FREEDOM to:
- Choose ANY symbol from the 28 available markets
- Decide when to enter and exit positions based on your analysis
- Set your own profit targets and risk tolerance
- Hold positions as long or short as you think optimal
- React to changing macro conditions and market data

Respond in this EXACT format:
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL> | NOTHING]
REASON: [Your reasoning citing macro + market data in 2-3 sentences]"""
```

---

## Quick Adjustments (Before Template System)

### Make Bot More Aggressive

**Edit**: `llm_agent/llm/prompt_formatter.py` line 171

**Change**:
```python
- NOTHING: No action (if conditions unclear or strategy suggests waiting)
```

**To**:
```python
- NOTHING: No action (only if market is extremely uncertain - prefer action over inaction)
```

**Add after line 178**:
```python
Remember: Fear & Greed below 30 often presents buying opportunities. 
Consider contrarian entries when RSI < 40 and macro context shows fear.
The goal is to make profitable trades, not just preserve capital.
```

### Encourage Contrarian Trading

**Add after line 178**:
```python
Strategy Guidance:
- When Fear & Greed Index < 30: Look for oversold opportunities (RSI < 40)
- When Fear & Greed Index > 70: Consider taking profits or shorting
- Don't wait for perfect setups - edge comes from acting when others hesitate
```

### Encourage Momentum Trading

**Add after line 178**:
```python
Strategy Guidance:
- Focus on tokens with strong momentum: RSI > 60, positive MACD, high volume
- Buy into strength when macro context is bullish
- Fear & Greed > 50 suggests risk-on environment - consider long positions
```

### Balance Risk/Reward

**Add after line 178**:
```python
Risk Management:
- Maximum position size: $30 per trade
- Maximum positions: 3 open at once
- Prefer trades with clear risk/reward ratio (e.g., 3:1 or better)
- But don't be overly conservative - small losses are acceptable for learning
```

---

## Proposed Template System (In Design)

**Status**: Design complete, implementation pending

### Template-Based System

**Directory Structure**:
```
llm_agent/
├── prompts/
│   ├── base.md                    # Base prompt
│   ├── swing_trading.md          # Swing trading (daily/weekly focus)
│   ├── aggressive.md              # More aggressive entries
│   ├── conservative.md            # Capital preservation
│   └── contrarian.md              # Contrarian entries
└── llm/
    └── prompt_formatter.py        # Loads templates
```

### Multi-Bot Support

**Run multiple bots simultaneously**:
```bash
# Bot 1: Swing trading (daily/weekly focus)
python3 -m llm_agent.bot_llm --config bot_configs/swing_trader.json --live &

# Bot 2: Aggressive
python3 -m llm_agent.bot_llm --config bot_configs/aggressive_bot.json --live &

# Bot 3: Conservative
python3 -m llm_agent.bot_llm --config bot_configs/conservative_bot.json --live &
```

**Each bot has**:
- Different prompt template
- Different position limits
- Different log file
- Independent decision making

### Multi-Timeframe Macro Context

**New requirement**: Macro context will include:
- **Daily context**: Events TODAY, 24h price movements, volume spikes
- **Weekly context**: Events THIS WEEK, 7-day trends, momentum
- **Long-term context**: Background only (not actionable for swing trading)

**Swing trading prompts** will emphasize daily/weekly context over long-term trends.

See `docs/MULTI_BOT_ARCHITECTURE.md` for full design.

---

## Testing Changes

**Before deploying changes**:

1. **Test in dry-run mode**:
   ```bash
   python3 -m llm_agent.bot_llm --dry-run --once
   ```

2. **Review decision**:
   ```bash
   python3 scripts/view_decision_details.py | tail -50
   ```

3. **Compare with previous**:
   - Check if decisions are more/less aggressive
   - Verify reasoning cites new guidance

4. **Deploy to live** (after validation):
   ```bash
   # Stop current bot
   pkill -f "llm_agent.bot_llm"
   
   # Restart with new code
   nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
   ```

---

## Example: More Aggressive Prompt

**Full modified instructions section**:

```python
instructions = """Instructions:
- Consider the macro context (overall market state, catalysts, outlook)
- Analyze current market data (price, volume, funding, OI, indicators)
- Review open positions (if any) and decide if you should CLOSE them or let them run
- Make ONE decision: BUY <SYMBOL>, SELL <SYMBOL>, CLOSE <SYMBOL>, or NOTHING
- Explain your reasoning citing SPECIFIC data sources

Decision Options:
- BUY <SYMBOL>: Enter new long position (only if room for more positions)
- SELL <SYMBOL>: Enter new short position (only if room for more positions)
- CLOSE <SYMBOL>: Close existing position (if it's time to exit based on your analysis)
- NOTHING: No action (ONLY if market is extremely uncertain - prefer action over inaction)

You have FULL FREEDOM to:
- Choose ANY symbol from the 28 available markets
- Decide when to enter and exit positions based on your analysis
- Set your own profit targets and risk tolerance
- Hold positions as long or short as you think optimal
- React to changing macro conditions and market data

Strategy Guidance:
- When Fear & Greed Index < 30: Look for contrarian buying opportunities (RSI < 40, oversold conditions)
- When Fear & Greed Index > 70: Consider taking profits or shorting overextended moves
- Don't wait for perfect setups - edge comes from acting when others hesitate
- The goal is to make profitable trades, not just preserve capital
- Small losses are acceptable for learning and market participation

Respond in this EXACT format:
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL> | NOTHING]
REASON: [Your reasoning citing macro + market data in 2-3 sentences]"""
```

---

## Monitoring Changes

**After making prompt changes**:

1. **Watch decisions**:
   ```bash
   tail -f logs/llm_bot.log | grep "LLM DECISION"
   ```

2. **Check decision breakdown**:
   ```bash
   python3 scripts/view_decisions.py
   ```

3. **Review reasoning**:
   ```bash
   python3 scripts/view_decision_details.py | grep -A 10 "Reason:"
   ```

**Metrics to watch**:
- NOTHING decisions (should decrease if more aggressive)
- BUY decisions (should increase if more aggressive)
- Reasoning quality (should still cite data sources)

---

## Troubleshooting

**If bot stops making decisions**:
- Check logs for errors
- Verify prompt format is correct
- Test with `--dry-run --once` first

**If decisions seem wrong**:
- Review reasoning in logs
- Check if data sources are working
- Verify macro context is fresh

**If bot becomes too aggressive**:
- Revert to original prompt
- Add more conservative guidance
- Adjust thresholds in strategy guidance

---

## Multi-Timeframe Macro Context (NEW REQUIREMENT)

### Current Problem

**Issue**: Macro context focuses on long-term trends (BTC dominance "high for months"), not actionable for swing trading.

**Example**:
- Current: "BTC dominance is 60% (high)" ← Not useful, this is a months-long trend
- Needed: "BTC dominance dropped 2% today, volume up 150% on SOL" ← Actionable for swing trading

### Solution

**Multi-timeframe macro context** will include:
- **Daily**: Events TODAY, 24h BTC dominance changes, volume spikes, funding rate changes
- **Weekly**: Events THIS WEEK, 7-day trends, momentum indicators
- **Long-term**: Background context only (for reference, not action)

**Swing trading prompts** will emphasize daily/weekly context and ignore long-term trends that don't change day-to-day.

See `docs/MULTI_BOT_ARCHITECTURE.md` for full design.

## Next Steps

1. ✅ **Try quick fix**: Edit prompt_formatter.py directly
2. ✅ **Test thoroughly**: Dry-run for 24 hours
3. ✅ **Monitor results**: Compare decision patterns
4. ⏳ **Implement multi-timeframe macro context**: Daily/weekly focus
5. ⏳ **Implement template system**: For easier future changes
6. ⏳ **Add multi-bot support**: Run multiple strategies simultaneously

See `AUDIT_REPORT.md` and `docs/MULTI_BOT_ARCHITECTURE.md` for full implementation plan.

