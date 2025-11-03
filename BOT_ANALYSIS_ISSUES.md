# Bot Trading Behavior Analysis

**Date**: 2025-10-31
**Issues Identified**: Bot only longing, ignoring most assets, not thinking strategically

---

## Issues Found

### 1. Bot Only Analyzing 3 Tokens (Ignoring 25 Assets)

**Problem**: The bot uses a two-stage process:
- **Stage 1**: LLM selects only **3 tokens** to analyze deeply via Deep42
- **Stage 2**: LLM makes trading decision based on those 3 tokens + market data table

**Current Code** (`llm_agent/llm/trading_agent.py` line 352):
```python
selected_tokens = self._select_tokens_to_analyze(available_tokens, num_tokens=3)
```

**Impact**: 
- Bot only gets deep analysis on 3 tokens (recently: PUMP, MEME, DOGE)
- Even though market data table has all 28 markets, bot focuses on the 3 it analyzed
- Missing opportunities across 25 other assets

**Recent Example**: Bot selected ['PUMP', 'MEME', 'DOGE'] and then chose BUY PUMP

---

### 2. Bot Only Taking Long Positions

**Problem**: 
- Recent decisions show only BUY (long) positions
- No SELL (short) decisions even when market is down
- Prompt encourages longs when Fear & Greed < 30 but doesn't encourage shorts when market is down

**Current Prompt** (v3_longer_holds.txt line 24):
```
- When Fear & Greed < 30: Look for contrarian LONG entries on oversold tokens (RSI < 40)
- When Fear & Greed > 70: Consider taking profits or SHORT entries on overbought tokens (RSI > 70)
```

**Issue**: 
- No guidance to SHORT when markets are down
- When Fear & Greed is low (29), it's told to look for LONG entries (contrarian)
- But if the market is actually trending down, shorts make more sense

---

### 3. Bot Not Thinking Strategically

**Problem**: 
- Bot makes quick decisions based on limited token analysis
- Doesn't compare multiple opportunities across all 28 markets
- Focuses on momentum ("strong bullish momentum") rather than strategic positioning

**Example from Recent Decision**:
```
Reason: Deep42 analysis shows PUMP with strong bullish momentum (+10.4% recently)...
Despite the Fear & Greed index at 29 (Fear), PUMP's high volume ($828M) and positive RSI (61)...
```

**Issue**: 
- Bot is chasing momentum instead of looking for strategic entries
- Not considering that if market is down, shorts might be better
- Not analyzing enough assets to find best opportunities

---

## Root Causes

1. **Token Selection Bottleneck**: Only 3 tokens analyzed deeply → bot ignores 89% of markets
2. **Prompt Bias**: Encourages longs during fear, doesn't encourage shorts during downtrends
3. **Limited Strategic Thinking**: Prompt doesn't require comparing multiple opportunities

---

## Proposed Solutions

### Fix 1: Analyze More Tokens (5-7 instead of 3)

**Change**: Increase `num_tokens` parameter in `_select_tokens_to_analyze()` from 3 to 5-7

**Impact**: Bot will analyze more assets, find better opportunities

---

### Fix 2: Add Strategic Short Guidance

**Change**: Update prompt to explicitly encourage shorts when:
- Market is trending down (multiple assets down 24h)
- Assets are overbought (RSI > 70) even if Fear & Greed is low
- Momentum is reversing

**New Prompt Addition**:
```
- When markets are DOWN (multiple assets negative 24h): Consider SHORT opportunities on overbought tokens (RSI > 70)
- When Fear & Greed < 30 BUT market is trending down: Consider SHORT positions on weak tokens, not just LONG on oversold
- Always evaluate SHORT opportunities alongside LONG opportunities - don't default to longs
```

---

### Fix 3: Require Multi-Asset Comparison

**Change**: Update prompt to require comparing multiple opportunities:

**New Prompt Addition**:
```
Before making a decision:
1. Review ALL 28 markets in the market data table
2. Identify top 3-5 opportunities (both LONG and SHORT)
3. Compare them based on: RSI, volume, funding rate, 24h change
4. Choose the BEST opportunity, not just the first one you see
5. Explain why you chose this symbol over others
```

---

## Recommended Next Steps

1. **Immediate**: Update prompt to encourage shorts and multi-asset comparison
2. **Short-term**: Increase token analysis from 3 to 5-7 tokens
3. **Medium-term**: Consider analyzing all 28 markets with a scoring system instead of just 3-7

---

## Current Bot Status

- **Prompt Version**: v3_longer_holds
- **Recent Decisions**: BUY PUMP, CLOSE DOGE
- **Decision Pattern**: Only longs, focusing on 3 tokens
- **Market Context**: Fear & Greed = 29 (Fear), market trending down

