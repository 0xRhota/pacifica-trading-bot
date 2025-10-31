# Moon Dev AI Trading Agent - Data Pipeline Research Index

## Research Completion Status

**Date**: October 29, 2025  
**Scope**: Complete analysis of Moon Dev's multi-exchange, multi-AI trading agent  
**Files Analyzed**: 20+ Python modules, 1000+ lines of code  
**Status**: COMPLETE - Ready for implementation

---

## Documentation Files Created

### 1. MOON_DEV_RESEARCH.md (PRIMARY REFERENCE)
**File**: `/Users/admin/Documents/Projects/pacifica-trading-bot/MOON_DEV_RESEARCH.md`  
**Length**: 1004 lines  
**Purpose**: Deep-dive technical documentation of Moon Dev's data pipeline

**Sections**:
- Executive Summary (overview of entire system)
- Section 1: Data Collection Code (Birdeye, HyperLiquid, Aster APIs)
- Section 2: Data Processing Pipeline (DataFrame, indicators, validation)
- Section 3: Prompt Construction for LLM (formatting market data)
- Section 4: Configuration System (settings hierarchy)
- Section 5: API Specifications (exact endpoints and formats)
- Section 6: Data Flow Diagram (visual representation)
- Section 7: Key Patterns to Copy for Pacifica
- Section 8: What Moon Dev Skips (simplifications)
- Section 9: What Moon Dev Should Add (recommendations)
- Section 10: Performance Benchmarks (timing data)
- Section 11: Critical Gotchas & Fixes (5 major pitfalls)
- Section 12: Integration Checklist for Pacifica
- Section 13: Example: Minimal Working Implementation

**Use This For**:
- Understanding the complete data pipeline
- API specification reference
- Technical indicator calculations
- Prompt formatting best practices
- Performance tuning
- Troubleshooting data issues

---

### 2. DATA_PIPELINE_IMPLEMENTATION_PLAN.md (ACTION PLAN)
**File**: `/Users/admin/Documents/Projects/pacifica-trading-bot/DATA_PIPELINE_IMPLEMENTATION_PLAN.md`  
**Length**: 500+ lines  
**Purpose**: Step-by-step implementation guide for Pacifica integration

**Phases**:
1. **Phase 1**: Core Data Collection (priority: IMMEDIATE)
2. **Phase 2**: Technical Indicator Processing (priority: HIGH)
3. **Phase 3**: LLM Prompt Construction (priority: HIGH)
4. **Phase 4**: LLM Integration (priority: HIGH)
5. **Phase 5**: Multi-Model Consensus (priority: MEDIUM, optional)
6. **Phase 6**: Trade Execution Integration (priority: MEDIUM)
7. **Phase 7**: Testing & Validation (priority: HIGH)
8. **Phase 8**: Configuration & Deployment (priority: MEDIUM)

**Includes**:
- Ready-to-use code templates for each phase
- Configuration examples
- Testing framework
- Deployment checklist
- Timeline estimates (9-13 days total)
- Success metrics

**Use This For**:
- Implementation roadmap
- Code templates to copy/modify
- Configuration setup
- Testing procedures
- Deployment steps

---

## Key Insights Summary

### Architecture
```
Moon Dev Data Pipeline:
  Fetch OHLCV 
    → DataFrame + Indicators 
    → Format as Text 
    → Query 6 AI Models in Parallel 
    → Calculate Consensus Vote 
    → Execute Trade
```

### For Pacifica
```
Pacifica Integration:
  Pacifica /kline 
    → pandas DataFrame 
    → pandas_ta Indicators 
    → Text Formatting 
    → Claude/GPT LLM 
    → Trading Decision 
    → Position Management
```

### Critical Technical Details

**Data Collection**:
- Birdeye (Solana): ~50-150ms per request
- HyperLiquid: ~100-200ms per request
- Automatic retry: 3 attempts, 10s timeout
- Caching: Local temp_data directory

**Data Processing**:
- Framework: pandas DataFrames
- Indicators: SMA(20), RSI(14), MACD, BBands via pandas_ta
- Type safety: All numeric columns cast to float64
- Error handling: Graceful degradation if indicators fail

**LLM Integration**:
- System prompt: Forces exactly 3-word responses (Buy/Sell/Nothing)
- Parallel execution: ThreadPoolExecutor for 6 models
- Consensus: Majority vote wins, confidence = winning_votes/total_votes
- Response time: 2-8s per model, 15-60s for swarm

**Configuration**:
- Precedence: trading_agent.py > config.py > .env
- Exchange selection: SOLANA, HYPERLIQUID, or ASTER (soon: PACIFICA)
- AI modes: Swarm (consensus, slow) or Single (fast)

---

## Copy-Paste Ready Code Patterns

### Pattern 1: Data Collection
```python
# 1. Fetch OHLCV
url = f"https://api.pacifica.fi/api/v1/kline"
params = {"symbol": "SOL", "interval": "15m", "start_time": start, "limit": 288}
response = requests.get(url, params=params, timeout=10)
data = response.json()

# 2. Convert to DataFrame
df = pd.DataFrame(data)
df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype('float64')

# 3. Cache
df.to_csv(f"temp_data/{symbol}_latest.csv", index=False)
```

### Pattern 2: Indicator Calculation
```python
import pandas_ta as ta

df['sma_20'] = ta.sma(df['close'], length=20)
df['rsi_14'] = ta.rsi(df['close'], length=14)
df['macd'] = ta.macd(df['close'])
df['bbands'] = ta.bbands(df['close'])
```

### Pattern 3: Prompt Formatting
```python
prompt = f"""
TOKEN: {symbol}
TIMEFRAME: 15m
LATEST 10 CANDLES:
{df.tail(10).to_string()}

DECIDE: Buy, Sell, or Do Nothing?
RESPOND: (only one word)
"""
```

### Pattern 4: LLM Voting
```python
from concurrent.futures import ThreadPoolExecutor

models = [('claude', client, 'claude-3-5-sonnet'), ('openai', client, 'gpt-4')]
votes = {}

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(_query_model, m, prompt): m for m in models}
    for future in futures:
        votes[futures[future]] = future.result(timeout=30)

majority = max(votes, key=votes.count)
confidence = votes.count(majority) / len(votes) * 100
```

---

## Implementation Priorities

### Immediate (Do First)
1. Read MOON_DEV_RESEARCH.md sections 1-3
2. Verify Pacifica API response format
3. Implement Phase 1: Data collection
4. Create unit tests for data validation

### This Week
5. Implement Phase 2: Indicators
6. Implement Phase 3-4: LLM integration
7. Create end-to-end test

### Next Week
8. Testing & backtesting (Phase 7)
9. Configuration & deployment (Phase 8)
10. Live paper trading

---

## Quick Reference Tables

### Data Collection Performance
| Source | Request Time | Response Format | Retry Logic |
|--------|--------------|-----------------|-------------|
| Birdeye | 50-150ms | JSON + unixTime | 3x, 10s timeout |
| HyperLiquid | 100-200ms | JSON array + ms | 3x, 10s timeout |
| Pacifica | TBD | TBD | 3x, 10s timeout |

### Technical Indicators
| Indicator | Library | Formula | Min Bars |
|-----------|---------|---------|----------|
| SMA(20) | pandas_ta | avg(close, 20) | 20 |
| SMA(50) | pandas_ta | avg(close, 50) | 50 |
| RSI(14) | pandas_ta | 100 × RS/(1+RS) | 14 |
| MACD | pandas_ta | 12EMA - 26EMA | 26 |
| BBands | pandas_ta | SMA ± (2×σ) | 20 |

### LLM Models Available
| Provider | Model | Cost | Speed | Reasoning |
|----------|-------|------|-------|-----------|
| Claude | Sonnet 3.5 | $3/$15/1M | Fast | Excellent |
| OpenAI | GPT-4 Turbo | $10/$30/1M | Medium | Excellent |
| DeepSeek | Chat | $0.55/$1.65/1M | Fast | Good |
| Groq | Grok-4 | $0.20/$0.50/1M | Very Fast | Good |

---

## Critical Gotchas to Avoid

### Gotcha #1: Timestamp Formats
**Problem**: Different APIs return timestamps in different units (Unix seconds vs milliseconds)
**Solution**: Always convert to datetime, then normalize

### Gotcha #2: Numeric String Conversions
**Problem**: API returns "45000.5" instead of 45000.5
**Solution**: Explicitly cast to float64: `df['close'] = df['close'].astype('float64')`

### Gotcha #3: Insufficient Data
**Problem**: Can't calculate SMA(50) with only 10 candles
**Solution**: Validate len(df) >= max_indicator_length before calculating

### Gotcha #4: Stale Cached Data
**Problem**: Old cached data used instead of fresh data
**Solution**: Delete temp cache before each run, or validate timestamps

### Gotcha #5: Model Timeouts
**Problem**: One model hangs, entire swarm stalls
**Solution**: Set timeout on futures.result(timeout=30)

---

## Integration Path for Pacifica

### Step 1: Data Collection
```
Implement fetch_pacifica_kline()
├─ Verify API response format
├─ Implement retry logic
├─ Test caching
└─ Validate data quality
```

### Step 2: Processing
```
Implement add_pacifica_indicators()
├─ Add SMA, RSI, MACD, BBands
├─ Test with 100+ candles
├─ Validate calculations
└─ Error handling
```

### Step 3: LLM
```
Implement PacificaTradingAgent()
├─ Format market data as text
├─ Query Claude/GPT
├─ Parse 3-word response
└─ Track confidence
```

### Step 4: Testing
```
Create test suite
├─ Unit tests (data, indicators)
├─ Integration tests (full pipeline)
├─ Backtest on historical data
└─ Paper trade 1 week
```

### Step 5: Deployment
```
Production launch
├─ Update configuration
├─ Set environment variables
├─ Deploy to production
└─ Monitor for issues
```

---

## File Locations

```
Research Documentation:
├─ MOON_DEV_RESEARCH.md (this directory)
├─ DATA_PIPELINE_IMPLEMENTATION_PLAN.md (this directory)
├─ RESEARCH_INDEX.md (this file)
└─ CLAUDE.md (project instructions)

Source Code to Implement:
├─ src/data/pacifica_collector.py (NEW)
├─ src/indicators/pacifica_indicators.py (NEW)
├─ src/agents/pacifica_prompt_formatter.py (NEW)
├─ src/agents/pacifica_trading_agent.py (NEW)
└─ tests/test_pacifica_pipeline.py (NEW)

Existing Files to Modify:
├─ src/data/ohlcv_collector.py (add Pacifica dispatch)
├─ config.py (add Pacifica settings)
└─ .env (add Pacifica credentials)
```

---

## How to Use These Documents

### For Understanding
1. Read MOON_DEV_RESEARCH.md top to bottom
2. Focus on sections 1-3 for data pipeline
3. Reference sections 7-11 for implementation tips

### For Implementation
1. Follow DATA_PIPELINE_IMPLEMENTATION_PLAN.md phases in order
2. Use code templates provided
3. Implement tests at each phase
4. Reference MOON_DEV_RESEARCH.md gotchas section when debugging

### For Quick Reference
1. Use RESEARCH_INDEX.md (this file) for quick lookups
2. Check "Copy-Paste Ready Code Patterns" for templates
3. Consult "Critical Gotchas" when issues arise

---

## Success Criteria

Track these metrics during implementation:

1. **Data Quality**: Pacifica candles < 5 minutes old
2. **Indicator Accuracy**: ±0.1% vs external sources
3. **LLM Response**: < 5 seconds per decision
4. **Consistency**: Same input always produces same output
5. **API Reliability**: 99%+ uptime on /kline endpoint
6. **Backtest**: Positive P&L over 30-day period

---

## Contact & Questions

This research was completed October 29, 2025.

For clarifications about the data pipeline or implementation:
1. Check MOON_DEV_RESEARCH.md for specifications
2. Check DATA_PIPELINE_IMPLEMENTATION_PLAN.md for implementation details
3. Verify Pacifica API response format against expected structure

---

END OF RESEARCH INDEX
