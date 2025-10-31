# LLM-Based Trading Agent - Implementation Plan

**Goal**: Build a single LLM trading agent that makes swing trading decisions based on quantitative market data, replicating the successful approach used by other teams.

**Date**: 2025-10-29

---

## Core Principles (From Reference Implementation)

### What They're Doing

> "They get to decide the 'style' of trading they engage in, but I'd describe it as swing trading, right now"

> "We feed them a variety of quantitative data that tries to capture the 'state' of the market at different granularities. Funding rates, OI, volume, RSI, MACD, EMA, etc"

### Critical Insight from Twitter Thread

**Tommy Raz** (@Trashmusen):
> "This won't work. They need to digest trade tape and build cvd. They need macro context. This might as well be a shitty rules based system given the limited data streams. Neat, I guess, but don't get too excited."

**Jay A** (@jay_azhang):
> "There is macro context encoded in quantitative data"

**Key Takeaway**: The quantitative metrics (funding, OI, volume indicators) already encode macro context. Don't overthink it - start with clean quant data feeds.

---

## Architecture Overview

### Single Agent System (Not Multi-Agent)

```
Market Data Pipeline → LLM Agent → Trade Decision → Execution → Performance Tracking
```

**Design Philosophy**:
- Plug-and-play LLM architecture (easily swap Grok, Claude, GPT-4, etc.)
- Start with one agent (Grok), optimize, then expand if needed
- Focus on data quality over complexity

---

## Phase 1: Market Data Pipeline

### Data Sources & Granularities

**Required Market State Inputs** (at multiple timeframes):

1. **Price & Volume Data**
   - OHLCV candles (15m, 1h, 4h, 1d)
   - Current price
   - 24h volume
   - Volume profile

2. **Derivatives Metrics**
   - **Funding rates** (current, 8h avg, 24h avg)
   - **Open Interest (OI)** (current, trend)
   - OI changes (% change 1h, 24h)

3. **Technical Indicators**
   - **RSI** (14, 21 periods on multiple timeframes)
   - **MACD** (12, 26, 9 standard)
   - **EMA** (9, 21, 50, 200)
   - Volume-weighted indicators

4. **Orderbook/Market Microstructure**
   - Bid/ask imbalance (what we already have)
   - Spread metrics
   - Depth analysis

### Data Format for LLM

**Goal**: Present data as structured, easy-to-parse JSON that encodes market state

Example structure:
```json
{
  "symbol": "SOL",
  "timestamp": "2025-10-29T19:56:00Z",
  "price": {
    "current": 235.50,
    "change_1h": -0.5,
    "change_24h": 2.3
  },
  "volume": {
    "24h": 1250000,
    "vs_avg_7d": 1.15
  },
  "funding": {
    "current": 0.0024,
    "8h_avg": 0.0031,
    "24h_avg": 0.0028
  },
  "open_interest": {
    "current": 82500000,
    "change_1h": -2.1,
    "change_24h": 5.4
  },
  "indicators": {
    "rsi_14": {
      "15m": 42,
      "1h": 55,
      "4h": 58
    },
    "macd": {
      "value": -1.2,
      "signal": -0.8,
      "histogram": -0.4
    },
    "ema": {
      "9": 234.20,
      "21": 233.10,
      "50": 230.50,
      "200": 225.00
    }
  },
  "orderbook": {
    "bid_depth": 959.27,
    "ask_depth": 2034.72,
    "imbalance": 0.47,
    "spread_pct": 0.01
  }
}
```

### Data Collection Tasks

- [ ] **Identify data sources**:
  - Pacifica API capabilities (check docs)
  - Cambrian API (we already have access)
  - External sources if needed (Coinglass, Glassnode, etc.)

- [ ] **Build data fetchers**:
  - Funding rate fetcher
  - OI fetcher
  - Technical indicators calculator
  - Candle data aggregator

- [ ] **Create market state snapshot function**:
  - Aggregates all data sources
  - Formats into LLM-friendly JSON
  - Caches/updates on interval

---

## Phase 2: LLM Agent Framework

### Agent Architecture

**Plug-and-Play LLM System**:
```python
class TradingAgent:
    def __init__(self, llm_provider="grok"):
        self.llm = self._init_llm(llm_provider)  # Swappable

    def analyze_market(self, market_state: dict) -> Decision:
        """Send market state to LLM, get trade decision"""
        prompt = self._build_prompt(market_state)
        response = self.llm.generate(prompt)
        return self._parse_decision(response)
```

### LLM Providers to Support

1. **Grok** (Start here - known to work well)
2. Claude (Sonnet 4.5)
3. GPT-4o
4. Gemini Pro
5. Open source options (Llama, etc.)

### Prompt Engineering

**System Prompt Template**:
```
You are a professional swing trader analyzing crypto markets.

Your trading style: Swing trading (holding positions for hours to days)

You will receive quantitative market data including:
- Price action and volume
- Funding rates and open interest
- Technical indicators (RSI, MACD, EMA)
- Orderbook metrics

Based on this data, decide:
1. Action: LONG, SHORT, or HOLD
2. Confidence: 0-100%
3. Reasoning: Brief explanation of your decision
4. Position size: suggested % of capital (10-50%)
5. Take profit levels: array of profit targets
6. Stop loss: percentage below/above entry

Output format: JSON only
{
  "action": "LONG|SHORT|HOLD",
  "confidence": 85,
  "reasoning": "...",
  "position_size_pct": 25,
  "take_profit": [0.03, 0.06, 0.10],
  "stop_loss": 0.02
}
```

**Context Window Management**:
- Include recent trade history (last 5 trades)
- Market regime (trending, ranging, volatile)
- Current portfolio state

### Decision Parsing

Agent must output structured decisions:
```python
@dataclass
class TradeDecision:
    action: str  # "LONG", "SHORT", "HOLD"
    confidence: float  # 0-100
    reasoning: str
    position_size_pct: float  # % of capital
    take_profit_levels: List[float]
    stop_loss_pct: float
    timestamp: datetime
```

---

## Phase 3: Execution & Risk Management

### Execution Logic

```python
def execute_decision(decision: TradeDecision, market_state: dict):
    # Validate decision
    if decision.confidence < MIN_CONFIDENCE_THRESHOLD:
        log("Low confidence, skipping")
        return

    if decision.action == "HOLD":
        return

    # Calculate position size
    capital = get_available_capital()
    position_value = capital * (decision.position_size_pct / 100)

    # Risk checks
    if not risk_manager.validate(position_value, decision.stop_loss_pct):
        log("Risk check failed")
        return

    # Place order
    place_order(
        symbol=market_state['symbol'],
        side="bid" if decision.action == "LONG" else "ask",
        size=calculate_size(position_value, market_state['price']['current'])
    )

    # Set stops and targets
    set_stop_loss(decision.stop_loss_pct)
    set_take_profit_ladder(decision.take_profit_levels)
```

### Risk Management Rules

- **Max position size**: 50% of capital
- **Min confidence threshold**: 60%
- **Max open positions**: 2-3 (swing trading)
- **Daily loss limit**: Circuit breaker
- **Correlation limits**: Don't open correlated positions

---

## Phase 4: Performance Tracking & Learning

### Metrics to Track

**Per Trade**:
- Entry/exit prices
- Hold time
- P&L (absolute and %)
- LLM reasoning
- Market conditions at entry
- What indicators were signaling

**Agent Performance**:
- Win rate
- Average win/loss
- Sharpe ratio
- Max drawdown
- Decision confidence vs outcome correlation

### Feedback Loop

**Future Enhancement** (not MVP):
- Feed past trade outcomes back to LLM
- "Here's what happened after your last decision..."
- Let agent learn from mistakes

---

## Implementation Roadmap

### Week 1: Data Infrastructure
- [ ] Audit available data sources (Pacifica, Cambrian, external)
- [ ] Build funding rate fetcher
- [ ] Build OI fetcher
- [ ] Implement technical indicators (TA-Lib or custom)
- [ ] Create `MarketState` aggregator class
- [ ] Test data pipeline end-to-end

### Week 2: LLM Agent Core
- [ ] Set up Grok API integration
- [ ] Design prompt templates
- [ ] Build agent class with decision parsing
- [ ] Test with mock market data
- [ ] Iterate on prompt engineering
- [ ] Implement decision validation

### Week 3: Execution & Integration
- [ ] Connect agent to Pacifica bot
- [ ] Implement risk management layer
- [ ] Add stop-loss/take-profit automation
- [ ] Create logging/monitoring dashboard
- [ ] Paper trade for 3-5 days

### Week 4: Live Testing & Optimization
- [ ] Start with small position sizes
- [ ] Monitor agent decisions vs outcomes
- [ ] Tune confidence thresholds
- [ ] Optimize data granularity
- [ ] Compare to existing orderbook strategy

---

## Data Source Research

### Pacifica API
- Check if they provide funding/OI endpoints
- Document available vs missing data
- Latency/update frequency

### Cambrian API
- We have access already
- Check for derivatives data
- OHLCV availability

### External APIs (if needed)
- **Coinglass**: Funding, OI, liquidations (free tier?)
- **Glassnode**: On-chain metrics
- **CryptoQuant**: Exchange flows
- **Binance/Bybit APIs**: Public derivatives data

---

## Technology Stack

### Data Collection
- `aiohttp` for async API calls
- `pandas` for data processing
- `TA-Lib` or `pandas-ta` for indicators
- `asyncio` for concurrent fetching

### LLM Integration
- Grok API client (to be implemented)
- `openai` library (compatible with most APIs)
- JSON schema validation

### Execution
- Existing Pacifica bot infrastructure
- Enhanced position management

### Monitoring
- Structured logging (JSON logs)
- Optional: Grafana/Prometheus
- CSV exports for analysis

---

## Key Decisions to Make

### 1. Data Update Frequency
- **Option A**: Every 15 minutes (aligned with candles)
- **Option B**: Every 5 minutes (more reactive)
- **Option C**: Event-driven (on significant changes)

**Recommendation**: Start with 15min for swing trading style

### 2. LLM Query Frequency
- **Option A**: On every data update
- **Option B**: Only when not in position
- **Option C**: Fixed schedule (e.g., every hour)

**Recommendation**: Only when not in position + periodic checks (every 4h) if holding

### 3. Position Management
- **Option A**: Agent decides when to exit
- **Option B**: Automated stops/targets only
- **Option C**: Hybrid (stops automated, can query agent for early exit)

**Recommendation**: Start with B (automated), evolve to C

### 4. Capital Allocation
- **Option A**: Fixed % per trade (e.g., always 30%)
- **Option B**: Let LLM decide (10-50% range)
- **Option C**: Kelly criterion based on confidence

**Recommendation**: B (LLM decides within bounds)

---

## Success Metrics

### MVP Success (4 weeks)
- ✅ Agent makes autonomous trading decisions
- ✅ Positions opened and closed automatically
- ✅ No crashes or stuck positions
- ✅ Decision logging for analysis
- ✅ At least break-even performance

### 3-Month Goals
- Win rate > 50%
- Sharpe ratio > 1.0
- Max drawdown < 15%
- Outperform simple orderbook strategy

---

## Risk Mitigation

### Technical Risks
- **LLM API downtime**: Fallback to rule-based system
- **Data source failures**: Multiple redundant sources
- **Bad decisions**: Strict risk limits + kill switch

### Trading Risks
- **Slippage**: Use limit orders when possible
- **Flash crashes**: Circuit breakers
- **Overtrading**: Cooldown periods
- **Black swans**: Position size limits

### Operational Risks
- **API costs**: Budget for LLM calls (~$0.01-0.10 per decision)
- **Monitoring**: Alerts for anomalies
- **Security**: No keys in logs/prompts

---

## Comparison to Reference Implementation

| Aspect | Their Approach | Our Approach |
|--------|---------------|--------------|
| LLM Strategy | Multiple competing agents | Single agent (start), scalable to multi |
| Trading Style | Swing trading | Swing trading ✅ |
| Data Inputs | Funding, OI, volume, indicators | Same ✅ |
| Platform | Hyperliquid | Pacifica (Solana) |
| Data Format | Quantitative at multiple granularities | JSON market state snapshots ✅ |
| Macro Context | Encoded in quant data | Same philosophy ✅ |

**Key Difference**: We start with one agent to optimize the system, then can easily add more by just instantiating multiple agents with different prompts/LLMs.

---

## Next Immediate Steps

1. **Data audit** (2 hours)
   - Check what Pacifica provides
   - Check what Cambrian provides
   - Identify gaps

2. **Design market state schema** (1 hour)
   - Finalize JSON structure
   - Define required vs optional fields

3. **Set up Grok API** (1 hour)
   - Get API key
   - Test basic completion
   - Measure latency

4. **Build first data fetcher** (2 hours)
   - Start with OHLCV + indicators
   - Test end-to-end

5. **Create simple agent** (2 hours)
   - Basic prompt
   - Parse decision
   - Log output

**Total: ~8 hours to first working prototype**

---

## File Structure

```
pacifica-trading-bot/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Abstract LLM agent
│   ├── grok_agent.py           # Grok implementation
│   └── decision.py             # Decision dataclass
├── data/
│   ├── __init__.py
│   ├── market_state.py         # Market state aggregator
│   ├── fetchers/
│   │   ├── funding_rates.py
│   │   ├── open_interest.py
│   │   ├── indicators.py
│   │   └── orderbook.py
│   └── schemas.py              # Data structures
├── execution/
│   ├── __init__.py
│   ├── executor.py             # Trade execution
│   └── risk_manager.py         # Enhanced risk checks
├── bots/
│   └── llm_agent_bot.py        # Main bot using LLM agent
├── docs/
│   ├── LLM_AGENT_STRATEGY_PLAN.md  # This doc
│   └── DATA_SOURCES.md         # Data source inventory
└── research/
    └── llm_trading/
        └── prompt_engineering.md
```

---

## Questions to Answer

- [ ] What's the Grok API endpoint and pricing?
- [ ] Does Pacifica provide funding rate data?
- [ ] Does Pacifica provide OI data?
- [ ] What technical indicator library should we use?
- [ ] How often do we want to pay for LLM calls? (cost optimization)
- [ ] Should we cache LLM decisions for similar market states?

---

## References

- Twitter thread: Tommy Raz / Jay A discussion on quantitative data encoding macro context
- Trading Strategy docs: https://tradingstrategy.ai/docs/index.html
- Our existing orderbook strategy: `strategies/long_short.py`
- Pacifica API docs: https://docs.pacifica.fi/

---

**Status**: PLANNING
**Next Action**: Data source audit
**Owner**: TBD
**Target MVP Date**: 4 weeks from start

---

## Research Findings: Potential Data Sources & Frameworks

### 1. TradingStrategy.ai ⭐⭐⭐

**What It Is**: Python-based algorithmic trading platform for DEX trading

**Capabilities**:
- ✅ **OHLCV candle data** from multiple DEXs (Uniswap, etc.)
- ✅ **Liquidity metrics** and price impact calculations
- ✅ **Technical indicators** (custom indicator support via decorators)
- ✅ **Live trading execution** (hot wallet, vault modes)
- ✅ **Backtesting framework** with performance metrics

**Limitations**:
- ❌ **No explicit funding rates** (DEX-focused, not perps)
- ❌ **No open interest data** (not derivatives-focused)
- ⚠️ Primarily for DEX spot trading, not perpetuals

**Verdict**: **NOT IDEAL** for our use case. Pacifica is perpetuals (like Hyperliquid), TradingStrategy.ai is spot DEX. Different market structure.

**Use Case**: Could be reference for data pipeline architecture, but wrong market type.

---

### 2. Moon Dev AI Agents ⭐⭐⭐⭐⭐

**What It Is**: Open-source collection of AI trading agents (100% free)

**Key Relevant Agents**:
- **Trading Agent** (`trading_agent.py`): Dual-mode system - single LLM or 6-model swarm consensus
- **Swarm Agent**: Queries Claude 4.5, GPT-5, Gemini 2.5, Grok-4, DeepSeek in parallel
- **Funding Agent**: Monitors funding rates across exchanges with AI analysis
- **Liquidation Agent**: Tracks liquidations with AI analysis
- **Chart Agent**: AI-powered chart analysis for buy/sell/hold decisions

**Data Sources Used**:
- HyperLiquid (perpetuals, funding rates)
- CoinGecko API (crypto market data)
- BirdEye API (Solana tokens)
- Twitter sentiment feeds

**Architecture Insights**:
- Multi-LLM consensus voting system
- Parallel execution (6 models queried simultaneously)
- Voice alerts for significant events
- Risk agent for portfolio management

**Verdict**: **HIGHLY RELEVANT** ⭐⭐⭐⭐⭐

**Why It's Perfect**:
1. ✅ Already built for perpetuals trading (HyperLiquid = similar to Pacifica)
2. ✅ Multi-LLM swarm architecture (exactly what we want to build toward)
3. ✅ Funding rate monitoring (one of our key data inputs)
4. ✅ Open source - can reference implementation patterns
5. ✅ Uses same LLMs we're targeting (Grok, Claude, GPT-4, etc.)

**Action Items**:
- [ ] Clone repo and study `trading_agent.py` architecture
- [ ] Review `funding_agent.py` for funding rate integration
- [ ] Study `swarm_agent.py` for multi-LLM consensus pattern
- [ ] Adapt their HyperLiquid data fetchers for Pacifica

**Key Learning**: They're doing EXACTLY what we want, just on HyperLiquid instead of Pacifica. We should heavily reference this codebase.

---

### 3. NOF1.ai / Alpha Arena ⭐⭐⭐⭐

**What It Is**: Live AI trading competition platform

**Competition Structure** (from screenshot analysis):
- **Models competing**: DeepSeek Chat V3.1, Claude 4.5 Sonnet, Gemini 2.5 Pro, GPT 5, Grok 4, Qwen 3 Max
- **Starting capital**: Each model gets $10,000 real capital
- **Market**: Crypto perpetuals on Hyperliquid
- **Objective**: Maximize risk-adjusted returns
- **Transparency**: All model outputs and trades are public
- **Duration**: Season 1 runs until November 3rd, 2025

**Leaderboard (from screenshot)**:
1. DeepSeek Chat V3.1: $22,501.60 (+125.02%)
2. Claude 4.5 Sonnet: $12,224.43 (+22.24%)
3. Gemini 2.5 Pro: $4,290.80 (-57.09%)
4. GPT 5: $4,039.38 (-59.61%)

**Key Insights**:
- **DeepSeek is dominating** (+125% vs everyone else)
- Models trade real markets with real capital
- Wide performance variance (125% to -59%)
- Proves LLM trading can be profitable (DeepSeek case)

**Architecture Clues**:
- Models get "identical prompts and input data"
- "Markets are perfect for this - dynamic, adversarial, open-ended"
- Real-time model chat/reasoning is logged

**Verdict**: **VALIDATION OF CONCEPT** ⭐⭐⭐⭐

**Why This Matters**:
1. ✅ Proves LLM trading works (DeepSeek +125%)
2. ✅ Same market (Hyperliquid perps, similar to Pacifica)
3. ✅ Same LLMs we're considering (Grok, Claude, GPT, DeepSeek)
4. ✅ Shows importance of model selection (DeepSeek >> others)

**Action Items**:
- [ ] Consider DeepSeek as primary model (not just Grok)
- [ ] Study why DeepSeek outperforms (reasoning quality? risk management?)
- [ ] Implement similar transparency (log all reasoning)
- [ ] Consider multi-model approach (hedge between DeepSeek + Grok)

---

### 4. Dexter (Financial Research Agent) ⭐

**What It Is**: Autonomous agent for deep financial research

**Capabilities**:
- Task decomposition for complex questions
- Autonomous tool selection
- Self-validation and iteration
- Financial statement analysis

**Data Sources**:
- Financial Datasets API (income statements, balance sheets, cash flows)
- OpenAI for LLM reasoning

**Verdict**: **NOT RELEVANT** for crypto trading

**Why**: Built for equity research (analyzing companies, not crypto). Different asset class, different data.

---

## Synthesis: What We Should Build

### Architecture Decision (Based on Research)

**Hybrid Approach**:
1. **Start Simple**: Single LLM (DeepSeek or Grok) like Alpha Arena
2. **Add Consensus**: Multi-LLM swarm like Moon Dev agents
3. **Prioritize Data**: Focus on funding rates, OI, indicators (Alpha Arena/Moon Dev proven inputs)

### Data Pipeline (Prioritized)

**Critical (Must Have)**:
1. ✅ Funding rates (Moon Dev `funding_agent.py` as reference)
2. ✅ Open Interest + changes
3. ✅ OHLCV candles (multiple timeframes)
4. ✅ Technical indicators (RSI, MACD, EMA)

**Important (Should Have)**:
5. Volume analysis
6. Liquidation data (Moon Dev `liquidation_agent.py`)
7. Orderbook metrics (we already have this)

**Nice to Have**:
8. Sentiment analysis
9. On-chain metrics
10. Whale tracking

### Model Selection (Based on Alpha Arena Results)

**Primary Candidates**:
1. **DeepSeek** ⭐⭐⭐⭐⭐ (+125% return in Alpha Arena)
2. **Grok** ⭐⭐⭐⭐ (Original plan, strong performance)
3. **Claude 4.5** ⭐⭐⭐ (+22% in Alpha Arena, reliable)

**Recommendation**: Start with DeepSeek (proven winner), add Grok as secondary

### Code References to Study

**Priority 1 (Study This Week)**:
- [ ] Moon Dev `trading_agent.py` - Core trading loop
- [ ] Moon Dev `swarm_agent.py` - Multi-LLM consensus
- [ ] Moon Dev `funding_agent.py` - Funding rate integration

**Priority 2 (Next Week)**:
- [ ] Moon Dev `risk_agent.py` - Risk management
- [ ] Moon Dev `liquidation_agent.py` - Liquidation monitoring

---

## Updated Implementation Plan

### Week 1: Moon Dev Code Study + Data Pipeline
- [ ] Clone and run Moon Dev agents locally
- [ ] Study their HyperLiquid data fetchers
- [ ] Adapt funding rate fetcher for Pacifica API (or external source)
- [ ] Implement OI fetcher
- [ ] Build market state aggregator (JSON format)

### Week 2: DeepSeek Integration
- [ ] Set up DeepSeek API (not Grok initially)
- [ ] Adapt Moon Dev agent patterns
- [ ] Build single-agent decision system
- [ ] Test with paper trading

### Week 3: Multi-Model Consensus (Optional Enhancement)
- [ ] Add Grok as secondary model
- [ ] Implement consensus voting (like Moon Dev swarm)
- [ ] Compare single vs swarm performance

### Week 4: Live Testing
- [ ] Start with $100 positions
- [ ] Monitor DeepSeek vs Grok decisions
- [ ] Iterate based on results

---

## Key Takeaways from Research

### What Alpha Arena Taught Us:
1. **DeepSeek works** (+125% proves concept)
2. **Model selection matters** (125% vs -59% spread)
3. **Transparency is key** (log all reasoning)
4. **Real markets = real validation**

### What Moon Dev Taught Us:
1. **Architecture is solved** (open source reference implementation)
2. **Multi-LLM consensus works** (6 models voting)
3. **Funding rates are critical** (dedicated agent for this)
4. **HyperLiquid = Pacifica analog** (both are perps DEXs)

### What TradingStrategy.ai Taught Us:
1. **Wrong market type** (spot DEX ≠ perps)
2. **Good for architecture reference** (data pipeline patterns)
3. **Skip for now** (focus on perps-specific tools)

---

## Revised Tech Stack

### LLM Providers
1. **DeepSeek** (primary - proven +125%)
2. **Grok** (secondary - diversification)
3. **Claude 4.5** (fallback - reliable)

### Data Sources
1. **Pacifica API** (prices, orderbook, positions)
2. **Cambrian API** (OHLCV, on-chain data)
3. **External funding/OI** (Coinglass or similar)
4. **Moon Dev patterns** (reference implementations)

### Frameworks
- Moon Dev agent architecture (adapt for Pacifica)
- Our existing bot infrastructure (execution layer)
- `asyncio` for concurrent data fetching
- `pandas` + `TA-Lib` for indicators

---

## Cost Estimates

### API Costs (Per Month)
- DeepSeek API: ~$20-50 (very cheap)
- Grok API: ~$50-100
- Funding/OI data: $0-50 (some sources free)
- **Total**: ~$70-200/month for full multi-model system

### Expected ROI
- Alpha Arena DeepSeek: +125% in ~2 weeks
- Even 10% monthly = $100+ profit on $1000 capital
- **Pays for itself quickly if it works**

---

**Status**: RESEARCH PHASE COMPLETE ✅
**Next Action**: Clone Moon Dev repo, study code, adapt for Pacifica
**Priority**: Focus on DeepSeek integration (not Grok initially)
**Timeline**: 4 weeks to MVP

