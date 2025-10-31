# Deep42 Custom Query Implementation

## Overview

The LLM trading bot now generates **custom Deep42 queries every 5 minutes** to get granular daily/weekly market context. This gives the AI time-specific intelligence about:
- Token launches and airdrops
- Protocol upgrades and updates
- Market-moving events scheduled for today/this week
- Breaking news and sentiment shifts

## Implementation

### Two-Step LLM Process

Every decision cycle (5 minutes):

1. **Step 1: Query Generation**
   - LLM analyzes current date and context
   - Generates a focused question to ask Deep42
   - Question targets daily/weekly catalysts relevant to trading decisions

2. **Step 2: Deep42 Execution**
   - Custom question sent to Deep42 API via `Deep42Tool`
   - Response received and formatted for prompt

3. **Step 3: Trading Decision**
   - Deep42 answer included at top of trading prompt
   - LLM makes trading decision with full context

### Example Queries Generated

```
"What are the most significant token unlocks, major protocol upgrades, or key economic calendar events scheduled for the Solana ecosystem between today (October 30, 2025) and the end of this week?"

"What are the most significant token launches, airdrops, or major protocol upgrades happening today, Thursday, October 30, 2025, specifically within the Solana ecosystem?"

"What are the most significant token unlocks, protocol upgrades, or major news events scheduled for today, Thursday, October 30, 2025, that could cause high volatility for Solana-based assets?"
```

### Example Deep42 Insight Used in Decision

**First Decision (2025-10-30 13:59)**:
- **Action**: NOTHING
- **Reasoning**: "Solana ETF debut today is expected to trigger profit-taking"

This shows the bot now understands **time-specific events** (Solana ETF launch TODAY) rather than just generic macro sentiment (alt season potential).

## Code Architecture

### Files Modified

1. **llm_agent/llm/deep42_tool.py** (NEW)
   - `Deep42Tool` class with `query(question: str)` method
   - Handles Deep42 API calls with custom questions

2. **llm_agent/llm/trading_agent.py**
   - Added `deep42_tool` instance
   - `_generate_deep42_query()` - LLM generates custom question
   - `_get_deep42_context()` - Execute query and format response
   - Modified `get_trading_decision()` to call Deep42 before macro context

3. **llm_agent/llm/prompt_formatter.py**
   - Added `deep42_context` parameter to `format_trading_prompt()`
   - Deep42 answer included at top of prompt (before macro context)

4. **llm_agent/bot_llm.py**
   - Pass `cambrian_api_key` to `LLMTradingAgent` initialization

### Prompt Structure (New)

```
Section 0: Custom Deep42 Query (Daily/Weekly Context)
Question: [LLM-generated question]
Deep42 Answer (Cambrian Network):
[Deep42's response]

Section 1: Macro Context (Market State)
[CoinGecko, Fear & Greed, general Deep42 analysis]

Section 2: Market Data (Latest)
[28 markets, OHLCV, indicators, funding, OI]

Section 3: Open Positions
[Current positions if any]

Section 4: Instructions
[Trading decision instructions]
```

## Cost Analysis

### LLM Costs (DeepSeek)
- **Query generation**: ~250 tokens input → ~$0.00004 per query
- **Trading decision**: ~2500 tokens input → ~$0.0004 per decision
- **Total per cycle**: ~$0.00044 per 5-minute cycle
- **Daily cost**: ~$0.13/day (288 cycles)
- **Monthly cost**: ~$3.90/month

### Deep42 Costs
- **Free** (using Cambrian API key: `doug.ZbEScx8M4zlf7kDn`)

## Benefits

### Before (Generic Macro)
- "Alt season potential has been discussed for weeks"
- High-level sentiment (bullish/bearish)
- No actionable daily/weekly context

### After (Custom Queries)
- "Solana ETF debut today is expected to trigger profit-taking"
- Time-specific events and catalysts
- Actionable intelligence for intraday decisions

## Future Enhancements

1. **Multi-query per cycle** - Ask 2-3 questions per cycle (daily, weekly, token-specific)
2. **Query history** - Track which questions led to profitable trades
3. **Adaptive questioning** - Learn which question styles yield best insights
4. **Position-specific queries** - Ask about open position tokens specifically

## Deployment

**Current Status**: ✅ **LIVE**
- **PID**: 76446
- **Started**: 2025-10-30 13:57:27
- **Mode**: LIVE trading on Pacifica DEX
- **Interval**: 5 minutes (300 seconds)
- **Cost**: ~$0.00044 per cycle (~$3.90/month)

**Command**:
```bash
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

**Stop Bot**:
```bash
pkill -f "llm_agent.bot_llm --live"
```

## Monitoring

**Logs**:
```bash
tail -f logs/llm_bot.log | grep "Generated Deep42 query"
```

**Recent Queries**:
```bash
grep "Generated Deep42 query" logs/llm_bot.log | tail -10
```

## Session Log

See `logs/bot_sessions.log` for detailed session history and deployment notes.
