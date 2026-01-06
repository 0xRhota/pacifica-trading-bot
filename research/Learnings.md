# Global Strategy Learnings

**Last Updated**: 2026-01-05
**Purpose**: Core reference for all trading strategies, results, and lessons learned

---

## Quick Reference: Active Bots

| Bot | Exchange | Strategy | Status |
|-----|----------|----------|--------|
| Lighter | Lighter DEX | light-short-bias-v1 | Active |
| Hibachi | Hibachi DEX | v9-qwen-enhanced | Active |
| Extended | Extended DEX | pairs-trade-v2-dynamic (Strategy D) | Active |
| Grid MM v8 | Paradex | Grid market making | Active |
| Pacifica | Pacifica.fi | V2 Deep Reasoning | Paused |

---

## Core Principles (Proven Across All Strategies)

### 1. Win Rate Does NOT Equal Profitability

**The Math:**
- 58% win rate can still lose money
- Why? Average loss > Average win

**Real Example - Paradex LLM Bot (Jan 2026):**
```
Win Rate: 58.3% (looks good!)
LONG WR: 62%
SHORT WR: 42.4%
Result: Account DECLINING
```

**Why it lost money:**
1. **Fees eat small wins**: 0.02% taker fee on Paradex means a 0.1% win becomes 0.06% after round-trip
2. **Funding rates**: Holding positions costs money (paid every 8 hours)
3. **Spread slippage**: Market orders lose the bid-ask spread (~0.5-3 bps depending on pair)
4. **Small wins, big losses**: Winners averaging +$0.15, losers averaging -$0.25

**Exchange Fee Comparison:**
| Exchange | Maker | Taker | Impact |
|----------|-------|-------|--------|
| Paradex | 0% (rebate) | 0.02% | Best for MM |
| Lighter | 0% | 0% | Best overall |
| Hibachi | Low | Low | Good |
| Extended | Variable | Variable | Check rates |

**Lesson**: Focus on **profit per trade** and **risk-adjusted returns**, not win rate.

Reference: `paradex_agent/bot_paradex.py`, `logs/trades/`

---

### 2. Adverse Selection is the Enemy (Market Making)

**What is it?** Getting filled often means you're on the wrong side.

**Why it happens:**
- Your buy gets filled = someone selling INTO you as price falls
- Your sell gets filled = someone buying FROM you as price rises
- Market makers get "picked off" during trends

**Grid MM Evolution (v1-v8):**

| Version | Change | Result | Lesson |
|---------|--------|--------|--------|
| v1 | Baseline 1 bps spread | +$0.48/10k | Low volume |
| v2 | Wider spread 2.5 bps | -$2.02/10k | Worse! Width doesn't help |
| v3 | Volatility adjustment | -$1.94/10k | Reactive = too slow |
| v4 | Inventory skewing | -$1.91/10k | Marginal improvement |
| v5 | Force close at 5 bps | -$1.47/10k | Better but locks in losses |
| v6 | Preemptive pausing | -$1.26/10k | ZERO force closes! |
| v7 | Min pause duration 20s | -$0.77/10k | Best efficiency |
| **v8** | Full history context | **+$1.81/10k** | **PROFITABLE** |

**Key Insight**: Prevention > Reaction. Pause orders BEFORE getting picked off.

Reference: `research/strategies/GRID_MM_EVOLUTION.md`, `scripts/grid_mm_v2.py`

---

### 3. Position Sizing Matters More Than Entry

**Small Account Reality ($23-$1000):**
- Risk per trade: 1-2% of account max
- Can't absorb multiple losses
- Need conservative sizing

**Hibachi Alpha Arena Success:**
```
Account: Started small
Result: +22.3% in 17 days
Win Rate: 30% (low!)
Secret: 3:1 R:R ratio, quality positions
```

**Position Sizing by Confidence (Hibachi/Extended):**
| Confidence | Leverage | Base % |
|------------|----------|--------|
| < 0.7 | 4x | 50% |
| 0.7-0.8 | 5x | 60% |
| 0.8-0.9 | 4x | 50% |
| > 0.9 | 3x | 40% |

Note: Very high confidence = overconfidence trap, so we reduce.

Reference: `hibachi_agent/execution/position_sizing.py`

---

### 4. SHORT Strategies Underperform LONG

**Paradex LLM Data:**
- LONG: 62% win rate
- SHORT: 42.4% win rate
- Difference: 20 percentage points!

**Why?**
1. Crypto has long-term upward bias
2. Funding rates often favor shorts (you pay to short)
3. Short squeezes are violent

**Rule**: Only SHORT when setup is SCREAMING:
- RSI > 75
- Clear rejection from resistance
- Multiple timeframe confirmation
- High confidence (>0.8)

Reference: `llm_agent/prompts_archive/v9_qwen_enhanced.md`

---

### 5. AI Context Quality = Recommendation Quality

**v8 Grid MM Breakthrough:**
- Qwen given only v5-v7 history → Recommended widening spread (WRONG)
- Qwen given FULL v1-v7 history → Recommended keeping tight spread (RIGHT)

**Why?** Without full context, AI repeats failed approaches.

**Best Practice**: Always reference:
- This learnings file
- Strategy evolution docs
- Past trade results

Reference: `research/strategies/GRID_MM_EVOLUTION.md`

---

## Strategy History: All Iterations

### Lighter Bot (17 versions)

| Version | Date | Key Change | Result |
|---------|------|------------|--------|
| deep42-v1 | Nov 13 | First Deep42 | Baseline |
| deep42-v2-patient | Nov 14 | +2% targets, -1.5% stops | Better |
| technicals-only-v1 | Nov 15 | Remove Deep42 panic | Improved |
| longer-holds-v1 | Nov 15 | 1.5-3% targets | Better |
| low-competition-swing-v1 | Nov 17 | Target <$50M OI pairs | Mixed |
| low-comp-swing-short-bias | Nov 17 | Bearish bias | Worse |
| **hard-exit-rules-v1** | Nov 17 | Hard exits override LLM | **Major improvement** |
| neutral-adaptive-v1 | Nov 18 | Remove hard bias | Better |
| aggressive-selective-v1 | Nov 18 | 2-5 positions max | Better |
| **light-short-bias-v1** | Nov 19 | **CURRENT** | **Active** |

**Key Lesson**: Hard exit rules (+2%/-1.5%, 2h min hold) were the breakthrough.

Reference: `logs/strategy_switches.log`, `lighter_agent/execution/hard_exit_rules.py`

---

### Hibachi Bot Evolution

| Version | Date | Key Change | Result |
|---------|------|------------|--------|
| fee-optimizer-v1 | Dec 4 | 2x leverage, 10min intervals | Baseline |
| dynamic-leverage-v1 | Dec 4 | Confidence-based leverage | Better |
| fee-optimized-v2 | Dec 5 | 10min intervals, 25 pos max | Better |
| aggressive-sizing-v6 | Dec 5 | 4-6x leverage | Mixed |
| **v9-qwen-enhanced** | Dec 15 | 5-signal scoring | **Alpha Arena Winner** |

**Alpha Arena Results:**
- +22.3% in 17 days
- 30% win rate
- Quality > quantity approach

Reference: `hibachi_agent/bot_hibachi.py`, `llm_agent/prompts_archive/v9_qwen_enhanced.md`

---

### Extended Bot Strategies

| Strategy | Description | Status |
|----------|-------------|--------|
| Strategy B | Hard exit rules | Archive |
| Strategy C | Copy whale 0x023a | Tested |
| **Strategy D** | ETH/BTC pairs trade | **CURRENT** |
| Strategy E | Self-improving pairs | Experimental |

**Strategy D (pairs-trade-v2-dynamic):**
- LLM picks direction (long stronger, short weaker)
- Hold 1 hour
- Close both legs
- Goal: Beat 50% via directional edge

Reference: `extended_agent/execution/strategy_d_pairs_trade.py`

---

### Pacifica Bot History

| Version | Description | Status |
|---------|-------------|--------|
| Pacifica v1 | Original implementation | Archive |
| Pacifica v2 | Deep reasoning strategy | Paused |
| V2 Deep Reasoning | Same as Lighter | Last active |

**Why Paused**: Moved focus to zero-fee exchanges (Lighter, Paradex).

Reference: `pacifica_agent/bot_pacifica.py`, `archive/2025-11-07-old-pacifica-framework/`

---

### Grid Market Making (Paradex)

| Version | P&L per $10k | Key Parameter |
|---------|--------------|---------------|
| v1 | +$0.48 | 1 bps spread |
| v2 | -$2.02 | 2.5 bps spread |
| v3 | -$1.94 | Volatility adjustment |
| v4 | -$1.91 | Inventory skewing |
| v5 | -$1.47 | Force close 5 bps |
| v6 | -$1.26 | Preemptive pausing |
| v7 | -$0.77 | 20s min pause |
| **v8** | **+$1.81** | Full context, 15s pause |

**v8 Winning Parameters:**
```python
spread_bps = 1.5        # Tight (v2-v4 proved wider doesn't help)
roc_threshold = 1.0     # Catch trends early
pause_duration = 15     # Seconds
inventory_limit = 25%   # Conservative
```

Reference: `scripts/grid_mm_live.py`, `research/strategies/GRID_MM_EVOLUTION.md`

---

## Failed Strategies (Lessons Learned)

### 1. Funding Rate Arbitrage
**What**: Delta-neutral between exchanges
**Why Failed**: Requires $10k+ capital. At $130: -$0.49 per cycle
**Lesson**: Some strategies need scale

Reference: `research/experiments/funding_arb_agent/`

### 2. Mean Reversion (RSI < 30 = Buy)
**What**: Buy oversold, sell overbought
**Why Failed**: Crypto trends hard, oversold gets more oversold
**Lesson**: Momentum > mean reversion in crypto

### 3. High-Frequency Scalping
**What**: Many small trades
**Why Failed**: Fees destroy profits even at 0.02%
**Lesson**: Need zero fees OR larger moves per trade

### 4. Deep42 Macro Overlays
**What**: Use AI sentiment to filter trades
**Why Failed**: "Risk-off" signals caused panic exits from winning trades
**Lesson**: Removed from core strategy (Nov 15)

Reference: `logs/strategy_switches.log` entry for technicals-only-v1

---

## Exchange-Specific Learnings

### Paradex
- **Fees**: 0% maker (rebate!), 0.02% taker
- **Best for**: Market making, earn rebates
- **Min notional**: $10 per order
- **Spreads**: Very tight on majors (0.5-1 bps)

### Lighter
- **Fees**: ZERO (both maker/taker)
- **Best for**: Any strategy (no fee drag)
- **Note**: LLM strategies tested here first

### Hibachi
- **Fees**: Low
- **Best for**: LLM directional trading
- **Note**: Alpha Arena competition venue

### Extended (Starknet)
- **Fees**: Variable
- **Best for**: Pairs trading
- **Note**: Requires Python 3.11+

---

## Decision Framework

### When to Use Grid MM:
- Zero/low maker fees (earn rebates)
- Sideways/ranging markets
- High liquidity pairs (BTC, ETH)
- Small account (predictable risk)

### When to Use LLM Directional:
- Clear trending market
- Strong technical setup (5-signal score >= 3)
- LONG-only bias (unless screaming SHORT setup)
- Can absorb drawdowns

### When to STOP Trading:
- Account declining despite high win rate
- Multiple consecutive losses
- No clear market direction
- Strategy parameters drifting from proven values

---

## Key Metrics to Track

1. **Profit per $10k volume** (Grid MM efficiency)
2. **Win rate by direction** (LONG vs SHORT)
3. **Average win vs average loss** (R:R ratio)
4. **Maximum drawdown** (risk management)
5. **Trade frequency** (overtrading indicator)
6. **Hold time distribution** (4+ hours = better)

---

## File References

| What | Where |
|------|-------|
| Grid MM Evolution | `research/strategies/GRID_MM_EVOLUTION.md` |
| Strategy Switches Log | `logs/strategy_switches.log` |
| LLM Prompts (13 versions) | `llm_agent/prompts_archive/` |
| Trade Logs | `logs/trades/` |
| Hard Exit Rules | `*/execution/hard_exit_rules.py` |
| Position Sizing | `*/execution/position_sizing.py` |
| Bot Entry Points | `*_agent/bot_*.py` |

---

## Research & Experiments

| Experiment | Location | Status |
|------------|----------|--------|
| High Volume Agent | `research/experiments/high_volume_agent/` | Research |
| Swing Trading Agent | `research/experiments/swing_trading_agent/` | Research |
| Funding Arb v1 | `research/experiments/funding_arb_agent/` | Failed |
| Funding Arb v2 (LLM) | `research/experiments/funding_arb_agent_v2/` | Experimental |

---

*This file should be referenced by Claude/Qwen before making strategy recommendations*
