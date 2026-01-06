# Pacifica Trading Bot - Development Progress

**Last Updated**: 2026-01-05
**Active Bots**: Grid MM (Paradex), Hibachi, Lighter, Extended

---

## 2026-01-05: Grid MM v8 Live + Dual-Agent Research

### Grid MM v8 Deployed to Paradex (LIVE)

**Goal**: Run the profitable v8 paper trading strategy on real money

**v8 Paper Trading Results** (reference):
- Volume: $6,549
- Fills: 37
- P&L: +$1.19 (+$1.81 per $10k)

**Issues Fixed During Live Deployment**:

1. **Order Sizing Below Minimum** (FIXED)
   - Problem: Inventory skew multipliers (0.3x) reduced $15 orders to $4.50 (below $10 min)
   - Fix: Enforce minimum notional before placement, conservative multipliers (min 0.67x)
   - File: `scripts/grid_mm_live.py`

2. **Signed Position Tracking** (FIXED)
   - Problem: `position_notional` always positive, SHORT positions handled incorrectly
   - Fix: Made `position_notional` signed (negative for SHORT)
   - Impact: Inventory limits now correctly allow orders that reduce position

3. **Excessive Order Cancellations** (FIXED)
   - Problem: Bot refreshing grid every 5 seconds (720 cancels/hour!)
   - Root Cause: I added `grid_interval = 5` which wasn't in v8 paper trading
   - v8 Paper Trading: Only refreshed on 0.25% price move or 80% inventory
   - Fix: Removed time-based refresh, now matches v8 exactly:
   ```python
   should_refresh = (
       fills > 0 or
       price_move_pct >= 0.25 or  # v8 behavior
       inventory_ratio > 0.8
   )
   ```

**Current Status**: Running on Paradex with $23 account
- PID: Active
- Symbol: BTC-USD-PERP
- Parameters match v8: 1.5 bps spread, 1.0 bps ROC, 15s pause

---

### Dual-Agent Self-Improving System (RESEARCH COMPLETE)

**Concept**: Run same strategy on Hibachi + Extended with hourly learning sync

**Research Findings** - What Transfers Between Exchanges:
| Pattern | Transfers? | Notes |
|---------|------------|-------|
| LONG vs SHORT bias | YES | Crypto-wide direction |
| Optimal hold times | YES | Market rhythm similar |
| RSI/MACD thresholds | YES | Technical patterns universal |
| Confidence calibration | YES | "0.8 conf = 60% accurate" |
| Symbol-specific rates | NO | Different assets per exchange |

**Proposed Architecture**:
```
HIBACHI BOT          EXTENDED BOT
     |                    |
     v                    v
  [Trades]             [Trades]
     |                    |
     +-----> HOURLY <-----+
             SYNC
              |
              v
    logs/shared_learnings.json
```

**Implementation Plan** (documented in TODO.md):
1. Phase 1: Shared learnings file schema
2. Phase 2: Hourly sync script
3. Phase 3: LLM prompt enhancement with cross-agent insights
4. Phase 4: Extended bot running Strategy F

**Existing Infrastructure**:
- `llm_agent/self_learning.py` - Already tracks win/loss, confidence calibration
- `hibachi_agent/execution/strategy_f_self_improving.py` - Auto-blocks poor performers

---

### Documentation Updates

1. **TODO.md** - Consolidated at root level (gitignored for local management)
   - Dual-agent system at top
   - Hetzner deployment plan
   - Self-analysis/memory system

2. **LEARNINGS.md** - Comprehensive rewrite (`research/LEARNINGS.md`)
   - All strategies documented (Lighter, Hibachi, Extended, Pacifica, Grid MM)
   - Real data and results tables
   - Explains WHY things work/fail (not just what)
   - Exchange fee comparison
   - Decision framework

3. **GRID_MM_EVOLUTION.md** - Updated with v8 profitable results

---

### Hibachi Trailing Stop Research (Qwen Consulted)

**User Idea**: Once position is up $2, set stop-loss at $2 to lock in gains

**Qwen's Analysis (2026-01-05)**:
1. **Worth implementing**: YES - locks in gains, complements asymmetric R:R strategy
2. **Fibonacci approach**: Can add value but not a silver bullet, use with other signals
3. **Gotchas to watch**:
   - Latency: Need low latency for stop execution
   - Slippage: Fast markets may execute at worse prices
   - Market impact: Large positions can move price

**Implementation Approach**:
```python
# Once profit >= $2:
# 1. Set stop-loss at entry + $2 (lock in gains)
# 2. Let position run beyond $2
# 3. Optionally trail stop using Fib levels
```

**Status**: Approved by Qwen, ready for implementation

---

## December 2025 Progress

### 2025-12-15: Strategy Ports & Alpha Arena Success
- **Hibachi**: Ported v9-qwen-enhanced from Lighter (Alpha Arena winner: +22.3% in 17 days)
  - 5-signal scoring system (RSI, MACD, Volume, Price Action, OI)
  - Score >= 3.0 to trade, asymmetric R:R (2:1 to 4:1)
  - Quality > quantity approach (30% WR but profitable)
- **Extended**: Strategy D v2 - Dynamic pairs trade with LLM direction
  - Qwen analyzes ETH vs BTC momentum, longs stronger, shorts weaker
  - Goal: Beat 50% via directional edge

### 2025-12-08: Deep42-Bias-v7 (Hibachi)
- Enabled Deep42 directional bias (live data, not hardcoded)
- Widened stop loss 1% → 2% (stop-hunting protection)
- Extended max hold 1hr → 2hr (let trends develop)
- Raised min_confidence 0.6 → 0.7

### 2025-12-05: Fee Optimization Sprint (Hibachi)
- **v2**: Interval 5m → 10m, max_positions 10 → 5, min_confidence 0.6 filter
  - Target: 50-70% fewer trades, same or better P/L
- **v6**: Aggressive sizing - base 40% → 60%, leverage 4-6x
  - Key insight: 0.7-0.8 confidence is sweet spot (best WR)
  - 0.8+ is overconfidence trap (reduce leverage)

### 2025-12-04: Strategy Pivots
- **Hibachi**: Dynamic leverage based on LLM confidence (1.5x-4x)
- **Extended**: Switched to BTC scalper whale copy (0x335f)
  - $2M account, ~35 trades/hr, 48.4% WR, BTC-only

### 2025-12-02: Performance Crisis Analysis
- **Extended**: -$53.20 (41.6% of capital), 37.5% WR
- **Hibachi**: -$20.74 (19.2% of capital), 45.8% WR
- Root causes identified:
  1. Wrong direction (shorting in bullish market)
  2. Asymmetric R:R (avg loss 5x larger than avg win)
  3. Overleveraging, stops too tight
- Full analysis: `research/bot_performance_analysis_2025-12-02.md`

---

## November 2025 Progress

### 2025-11-27: Copy Trading Pivot
- Whale wallet analysis for Extended bot
- Fast exit monitor implementation
- Strategy A/B testing framework

### 2025-11-24: Hibachi Integration
- Full API integration complete
- Order execution verified
- Bot ready for live trading

### 2025-11-15: Longer-Holds V1 Strategy
- Removed Deep42 panic selling
- Guidance-based approach (not rule-based)
- Let winners run to 1.5-3%, cut losses at 0.5%

### 2025-11-14: Deep42-V2-Patient Strategy
- Added 30-minute minimum hold time
- Reduced risk-off paranoia
- Profit tier exit logic

### 2025-11-10: Confidence-Based Hold Logic
- High confidence (≥0.7): 2 hour minimum hold
- Trade tracker stores confidence scores
- Performance analysis: 47.3% win rate on 1,009 trades

### 2025-11-09: Exchange Data Only
- Fixed tracker JSON sync issues
- Created exchange-only performance checker
- Source of truth: Exchange API only

### 2025-11-08: V4 Momentum Strategy
- Switched from mean reversion to momentum
- RSI > 50, MACD positive (not RSI < 30 oversold)
- Position size reduced until win rate improves

### 2025-11-07: Multi-Bot Architecture
- Pacifica bot fully operational
- Lighter bot running in parallel
- 95% shared code, different exchange APIs

---

## Active Bot Status

| Bot | Exchange | Strategy | Status |
|-----|----------|----------|--------|
| Grid MM v8 | Paradex | Preemptive pausing | LIVE |
| Lighter | Lighter DEX | light-short-bias-v1 | Active |
| Hibachi | Hibachi DEX | v9-qwen-enhanced | Active |
| Extended | Extended DEX | Strategy D pairs | Active |

---

## Key Files Reference

| Purpose | File |
|---------|------|
| Grid MM Live | `scripts/grid_mm_live.py` |
| Strategy Learnings | `research/LEARNINGS.md` |
| Grid MM Evolution | `research/strategies/GRID_MM_EVOLUTION.md` |
| Self-Learning | `llm_agent/self_learning.py` |
| Strategy F | `hibachi_agent/execution/strategy_f_self_improving.py` |
| TODO List | `TODO.md` (root, gitignored) |

---

*This document tracks development progress. For strategy details, see LEARNINGS.md*
