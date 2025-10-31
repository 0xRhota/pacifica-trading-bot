# Dynamic Token Analysis & Position Re-evaluation

## Overview

The LLM trading bot now has **full freedom to discover and analyze any tokens** on HyperLiquid, selecting different tokens to analyze each 5-minute cycle. It also **re-evaluates open positions** with Deep42 analysis.

## Key Features

### 1. Token Discovery (HyperLiquid)
- Fetches 218 available perpetual markets from HyperLiquid
- Sorted by Open Interest (most liquid first)
- Updates every cycle (5 minutes)

### 2. Dynamic Token Selection
- **LLM chooses 3 tokens to analyze in depth each cycle**
- No pre-defined list - total freedom
- Selection based on:
  - Recent news and catalysts
  - Price action and volatility
  - Trending narratives
  - Mix of majors and altcoins

### 3. Deep Token Analysis
- Gets Deep42/Cambrian analysis for each selected token:
  - Current sentiment and social metrics
  - Recent news and developments
  - Technical factors (support/resistance, momentum)
  - Catalysts in next 24-48 hours
  - Risks and concerns

### 4. Position Re-evaluation
- For each open position, gets Deep42 evaluation:
  - Entry vs current price
  - P&L percentage
  - Time held
  - **Recommendation: close or hold?**
  - Market conditions and catalysts

## Decision Flow (Every 5 Minutes)

```
Step 1: Custom Deep42 Macro Query
└─> LLM generates question about daily/weekly events
    └─> Deep42 answers with time-specific intelligence

Step 2: Token Discovery
└─> Fetch 218 tokens from HyperLiquid (sorted by OI)

Step 3: Token Selection
└─> LLM selects 3 tokens to analyze
    Examples: PUMP, MEME, BOME
              SOL, BTC, PENGU
              ETH, HYPE, SUI

Step 4: Token Deep Dives
└─> Get Deep42 analysis for each selected token
    └─> Sentiment, news, technicals, catalysts

Step 5: Position Evaluations (if positions open)
└─> Get Deep42 evaluation for each open position
    └─> "Should I close or hold?"

Step 6: Fetch Market Data
└─> 28 Pacifica markets (OHLCV, indicators, funding, OI)

Step 7: Trading Decision
└─> LLM decides: BUY, SELL, CLOSE, or NOTHING
    With full context from all previous steps
```

## Example Decision Cycle

### Inputs Gathered

**1. Custom Macro Query:**
```
Q: "What are the most significant token launches, airdrops, or major protocol
    upgrades happening on Solana today, Thursday, October 30, 2025?"

A: [Deep42 analysis mentioning Solana ETF debut, potential profit-taking, etc.]
```

**2. Tokens Selected by LLM:**
- PUMP
- MEME
- BOME

**3. Token Analyses:**
```
--- PUMP Analysis (Deep42/Cambrian) ---
Sentiment: 96.5% bullish
Recent News: Strong meme momentum, whale accumulation
Technical: Breaking resistance at $0.45
Catalysts: Potential CEX listing rumored
Risks: High volatility, speculative asset

--- MEME Analysis ---
[Similar detailed analysis]

--- BOME Analysis ---
[Similar detailed analysis]
```

**4. Position Evaluations:**
```
(None - no open positions this cycle)
```

**5. Market Data Table:**
```
28 markets with price, volume, funding, OI, RSI, MACD, etc.
```

### LLM Decision:

**Action:** NOTHING

**Reasoning:**
> "The macro context shows a Fear & Greed Index at 34/100 indicating market fear,
> with BTC dominance at 57.88% suggesting capital rotation away from alts. Most
> assets show oversold RSI readings (SOL at 31, ETH at 33) but lack clear bullish
> catalysts, and the Deep42 analysis confirms no major token launches or protocol
> upgrades today to drive momentum. While PUMP shows extremely bullish sentiment
> (96.5%), [...]"

## Implementation Details

### Files Created

**llm_agent/llm/token_analysis_tool.py**
- `TokenAnalysisTool` class
- `get_available_tokens()` - Fetch from HyperLiquid
- `analyze_token(symbol)` - Get Deep42 analysis
- `evaluate_position(...)` - Get Deep42 position evaluation

### Files Modified

**llm_agent/llm/trading_agent.py**
- `_select_tokens_to_analyze()` - LLM picks tokens
- `_get_token_analyses()` - Get Deep42 for selected tokens
- `_get_position_evaluations()` - Get Deep42 for positions
- Updated `get_trading_decision()` flow

**llm_agent/llm/prompt_formatter.py**
- Added `token_analyses` parameter
- Added `position_evaluations` parameter
- Updated prompt structure

### Prompt Structure (New)

```
Section 0: Custom Deep42 Query (Daily/Weekly Context)
Question: [LLM-generated]
Answer: [Deep42 response]

Section 0.5: Selected Token Deep Dives
--- PUMP Analysis (Deep42/Cambrian) ---
[Full analysis...]

--- MEME Analysis (Deep42/Cambrian) ---
[Full analysis...]

--- BOME Analysis (Deep42/Cambrian) ---
[Full analysis...]

Section 0.75: Open Position Evaluations
--- ETH LONG Position Evaluation (Deep42/Cambrian) ---
Entry: $3,780.05, Current: $3,775.95, Time: 42 minutes
[Evaluation: should close or hold?]

Section 1: Macro Context (Market State)
[CoinGecko, Fear & Greed, general Deep42 analysis]

Section 2: Market Data (Latest)
[28 markets table with all technicals]

Section 3: Open Positions Summary
[Position table if any exist]

Section 4: Trading Instructions
[Decision format and guidelines]
```

## Cost Analysis

### LLM Costs (DeepSeek)
- **Macro query generation**: ~250 tokens → ~$0.00004
- **Token selection**: ~300 tokens → ~$0.00005
- **3x Token analyses**: 3 Deep42 calls (free via Cambrian)
- **Position evaluations**: Variable (free via Cambrian)
- **Trading decision**: ~6,000 tokens → ~$0.0009
- **Total per cycle**: ~$0.001 per 5-minute cycle

### Daily & Monthly Costs
- **Per hour**: $0.012 (12 cycles)
- **Per day**: $0.29 (288 cycles)
- **Per month**: $8.64 (24/7 operation)

### Deep42/Cambrian Costs
- **FREE** (using API key: `doug.ZbEScx8M4zlf7kDn`)

## Benefits

### Before (Fixed 28-Token Analysis)
- Only analyzed Pacifica's 28 markets
- No deep dives on specific tokens
- Generic macro context
- No position re-evaluation

### After (Dynamic Discovery)
- **218 tokens available** (HyperLiquid universe)
- **LLM picks 3 to analyze deeply** each cycle
- Different tokens each time (PUMP, MEME, BOME → SOL, BTC, ETH → ...)
- **Sentiment + news + catalysts** for selected tokens
- **Position re-evaluation** with "close or hold?" advice
- Time-specific intelligence (daily/weekly)

## Example Token Selections

The LLM has full freedom to select any 3 tokens. Examples from different cycles:

**Cycle 1 (Memecoin Focus):**
- PUMP, MEME, BOME

**Cycle 2 (Major + Alts):**
- BTC, ETH, SOL

**Cycle 3 (Trending Narratives):**
- PENGU, HYPE, SUI

**Cycle 4 (Catalyst-Driven):**
- Token with upcoming unlock
- Token with new partnership
- Token with protocol upgrade

## Position Re-evaluation Example

```
--- SOL LONG Position Evaluation (Deep42/Cambrian) ---
Entry: $182.50, Current: $179.20, Time: 3 hours
P&L: -1.81%

Deep42 Evaluation:
"Given SOL's current position near key support at $178, with the Solana ETF
launch creating short-term volatility but strong institutional interest, I
recommend holding this position. The oversold RSI at 31 suggests a potential
bounce, and the -1.81% P&L is within normal pullback range. Consider adding
a stop-loss at $175 (5% drawdown) to protect downside, but the broader trend
remains bullish with $195-200 targets achievable within 48-72 hours if BTC
maintains above $68k."
```

The LLM then uses this evaluation to decide whether to:
- **CLOSE SOL** (take the small loss)
- **NOTHING** (hold the position)
- **BUY more** (if very bullish)

## Monitoring

### Check Recent Token Selections
```bash
grep "LLM selected tokens" logs/llm_bot.log | tail -20
```

### Check Token Analyses
```bash
grep "Deep42 token analysis" logs/llm_bot.log | tail -10
```

### Check Position Evaluations
```bash
grep "position evaluation" logs/llm_bot.log | tail -10
```

## Bot Status

🟢 **LIVE** (PID: 88790)
- **Started**: 2025-10-30 14:10:20
- **Mode**: LIVE trading on Pacifica DEX
- **Interval**: 5 minutes (300 seconds)
- **Features**:
  - ✅ Custom Deep42 macro queries
  - ✅ Dynamic token discovery (218 markets)
  - ✅ LLM-selected token deep dives (3 per cycle)
  - ✅ Position re-evaluation (if positions open)
  - ✅ Full market data (28 Pacifica markets)

**Command:**
```bash
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

**Stop Bot:**
```bash
pkill -f "llm_agent.bot_llm --live"
```

## Future Enhancements

1. **Adjust number of tokens** - Analyze 2-5 tokens based on market conditions
2. **Token history** - Track which tokens led to profitable trades
3. **Adaptive selection** - Learn which token types to focus on
4. **Portfolio correlation** - Avoid correlated positions
5. **Multi-timeframe** - Analyze tokens on different timeframes
6. **Social sentiment** - Integrate Twitter/Reddit sentiment

## Documentation

See also:
- `DEEP42_CUSTOM_QUERIES.md` - Custom macro query implementation
- `DATA_SOURCES_SUMMARY.md` - All data sources with attribution
- `logs/bot_sessions.log` - Detailed session history
