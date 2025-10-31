# Project Progress Log

**Format**: [DATE] Status | Key Work | Next Steps

---

## 2025-10-31

**Status**: Prompt Experimentation | Bot Running LIVE (PID: 11153) | v3_longer_holds

**Prompt Version History**:

### Version 3 - Longer Holds + Position Management (CURRENT - 2025-10-31 15:16)
**File**: `llm_agent/llm/prompt_formatter.py` lines 160-203
**Changes**:
- Added "POSITION MANAGEMENT (CRITICAL)" section:
  - Fee consideration: $0.02 per trade, need 0.5-1% profit to overcome fees
  - **When to CLOSE**: Profit target (+1.5-3%), Stop loss (-1-1.5%), Clear reversal, Better opportunity
  - **DO NOT close**: Just because position is "flat" after a few minutes - swing trades need time
  - **DO NOT close** prematurely: If moving in right direction, let it run
  - "Think in terms of swing moves" - develop over hours/days
- Keeps all v2 swing trading strategy guidance

**Bot Restarted**: PID 11153 at 15:16
**Goal**: Fix premature position closing (was closing after 8 min, fees eating profits)
**Problem Solved**: Bot was closing positions too quickly, breaking even or small losses due to fees
**Expected Behavior**: Hold positions longer, close fast at profit/loss targets
**Revert Command**: `./scripts/swap_prompt.sh v2_aggressive_swing`

### Version 2 - Aggressive Swing Trading (2025-10-31 14:38 - 15:16)
**File**: `llm_agent/llm/prompt_formatter.py` lines 160-191
**Changes**:
- Changed NOTHING from "if conditions unclear" → "ONLY if extremely uncertain - prefer action over inaction"
- Added "SWING TRADING STRATEGY" section with:
  - Focus on daily/weekly movements, not long-term trends
  - Look for 24h volume spikes >50%
  - Contrarian entries: Fear & Greed < 30 + RSI < 40 = LONG
  - Profit taking: Fear & Greed > 70 + RSI > 70 = SHORT
  - "Don't wait for perfect setups"
  - "Short-term volatility is opportunity, not risk"
  - "Small losses acceptable - goal is profitable trades, not preservation"

**Bot Ran**: PID 93626 (14:38 - 15:16)
**Issue Found**: Closing positions too early (8 minutes), fees eating profits
**Superseded By**: Version 3
**Revert Command**: `./scripts/swap_prompt.sh v2_aggressive_swing`

### Version 1 - Baseline Conservative (2025-10-30)
**File**: `llm_agent/llm/prompt_formatter.py` lines 160-182
**Behavior**: Conservative, waits for clear conditions, no specific strategy guidance
**Preserved in git**: Commit `76e6dfe` (can revert to this)

---

## 2025-10-30

**Status**: Critical Bugs Fixed | LLM Bot Running LIVE (PID: 7213)

**Bugs Fixed**:
1. ✅ **Sub-cent token price display** - PUMP/kBONK/kPEPE showing $0.00 instead of actual prices
   - Root cause: Fixed 2-decimal formatting rounded <$0.01 prices to zero
   - Fix: Dynamic decimal places (6 for <$0.01, 4 for <$1, 2 for ≥$1)
   - Files: `llm_agent/data/aggregator.py`, `llm_agent/llm/prompt_formatter.py`
   - Impact: Bot was making decisions on wrong data (closed PUMP thinking -100% P&L when price "barely moved")

2. ✅ **Position enrichment missing** - No current_price or P&L in position data
   - Root cause: `_fetch_open_positions()` only returned basic API fields
   - Fix: Added orderbook price fetching and real-time P&L calculation
   - File: `llm_agent/bot_llm.py`
   - Impact: LLM now sees actual position performance instead of N/A

3. ✅ **Lot size execution failures** - SUI order rejected for floating point precision
   - Root cause: Config missing many tokens (only 16/28 markets), floating point errors
   - Fix: Added all 28 lot sizes from Pacifica API, used Decimal library for exact calculations
   - Files: `config.py`, `llm_agent/execution/trade_executor.py`
   - Impact: Orders will now execute correctly for all 28 markets

4. ✅ **Decision viewer output cleanup** - Hard to read, entries bleed together
   - Fix: Block character separators, show counts instead of lists, conditional detail display
   - File: `scripts/view_decision_details.py`

**Data Integrity Verified**:
- ✅ All data from real APIs (Pacifica, HyperLiquid, Binance)
- ✅ No hallucinated or fabricated data
- ✅ Price, volume, funding, OI, RSI, MACD, SMA all traced to source

**Technical Details**:
- All 28 lot sizes sourced from Pacifica `/info` endpoint
- Decimal arithmetic prevents floating point precision errors
- Dynamic price formatting preserves sub-cent token accuracy

**Active Bot**:
- Running: `llm_agent/bot_llm.py` (PID: 7213)
- Mode: LIVE (real trades)
- Strategy: LLM-driven with Deep42 sentiment + dynamic token analysis
- Check interval: 5 minutes
- Position size: $30/trade
- Max positions: 3

**Next**:
- Monitor execution success rates in logs
- Verify lot size fixes work for all tokens
- Continue LLM decision tracking

---

## 2025-10-29

**Status**: Planning LLM Trading Agent | Current bot running

**Research Completed**:
- ✅ Moon Dev AI agent architecture analyzed (1196 lines trading_agent.py, 568 lines swarm_agent.py)
- ✅ Data patterns documented: OHLCV → indicators (SMA, RSI, MACD, BBands) → DataFrame.to_string() → LLM
- ✅ Swarm consensus: 6 models vote in parallel (DeepSeek dominated Alpha Arena at +125%)
- ✅ Cambrian API endpoints mapped: Deep42 social sentiment, token metrics, OHLCV, security scores
- ✅ Pacifica API funding rates discovered: /info endpoint has all 28 markets with current + next funding
- ✅ Funding rate comparison: Binance (best), Bybit, OKX all working, no auth required

**Data Sources Confirmed**:
- Cambrian: Token details, OHLCV, security, Deep42 AI social sentiment
- Pacifica: Kline, orderbook, positions, funding rates (28 markets)
- External: Binance/Bybit funding rates (free, no auth)

**Active Bot**:
- Running: `bots/live_pacifica.py` (PID: 55194)
- Strategy: LongShortStrategy (orderbook imbalance 1.3x)
- Balance: $136.60 Pacifica
- Symbols: SOL, BTC, ETH, PENGU
- No positions yet (waiting for signal)

**Documentation Created**:
- `docs/DATA_SOURCES.md` - Complete API reference with examples
- `logs/bot_sessions.log` - Condensed session tracking

**Next Steps**:
1. Add CAMBRIAN_API_KEY to .env (user to provide)
2. Set up DeepSeek API integration
3. Build market state aggregator (OHLCV + indicators + funding + sentiment)
4. Create LLM agent framework for Pacifica
5. Test single-model decision making
6. Implement swarm consensus (optional)

**Key Insight**: "DATA matters more than strategies - LLM handles the logic" (user feedback)

**Foundational Concept** (Jay A Twitter Thread):
- Skeptic: "This won't work. Need trade tape, CVD, macro context. Just a shitty rules based system."
- Jay A Response: **"There is macro context encoded in quantitative data"**
- Implementation: "We feed them funding rates, OI, volume, RSI, MACD, EMA, etc to capture 'state' of market at different granularities"
- Result: LLMs decide their own trading style (swing trading currently) based on multi-granularity market state
- **This is what we're reverse engineering**

---

## Archive

### 2025-10-08
- Bot ran with SOL/PENGU positions
- Hit config errors (PacificaConfig.MAX_LOSS_THRESHOLD missing)
- Stopped without positions closed

### Earlier
- Security audit after ETH private key leak (Lighter wallet drained)
- Confirmed Pacifica only needs API keys (no wallet private keys)
- Fixed bot to use API Agent Keys method
