# Qwen High Volume Strategy Analysis
## Date: November 27, 2025

---

## The Brutal Truth

> **"High volume (50+ trades/day) is mathematically unprofitable"** due to fees (5-7% daily fees).

However, **10-20 trades/day with 25% win rate and 4:1 R/R can yield +1-2% daily profit**.

---

## The Math That Matters

### Why Previous Strategies Failed

| Strategy | Win Rate | R/R | Required Win Rate | Result |
|----------|----------|-----|-------------------|--------|
| LLM Scalping | 22.7% | 1:2 (backwards) | 68% | **LOSS** |
| Funding Arb | N/A | N/A | N/A | **LOSS** (capital too small) |

### What Works Mathematically

| R/R Ratio | Required Win Rate | Fees Impact |
|-----------|-------------------|-------------|
| 1:1 | 55% | Very hard |
| 2:1 | 37% | Hard |
| 3:1 | 28% | Achievable |
| **4:1** | **22%** | **Best option** |

### The Winning Formula

```
R/R = 4:1 (4% take profit, 1% stop loss)

With 20 trades/day at 25% win rate:
- 5 wins × 3.9% (4% - 0.1% fee) = +19.5%
- 15 losses × -1.1% (1% + 0.1% fee) = -16.5%
- NET: +3% daily profit

With $100 capital = $3/day profit
With $500 capital = $15/day profit
```

---

## Qwen's Recommended Strategy

### "Adaptive Trend Following with Time Limits"

**Parameters:**
- Capital: $100-500
- Assets: BTC, ETH, SOL
- Timeframe: **1-hour candles** (not 5-min scalping)
- Trades per day: **10-20** (not 50+)
- Position size: **1% of capital per trade**

### Entry Signals (ALL must be true)

**FOR LONGS:**
1. Price > 50-period SMA (uptrend)
2. RSI(14) < 30 AND rising (oversold but recovering)
3. Volume > 200-period average (momentum confirmed)

**FOR SHORTS:**
1. Price < 50-period SMA (downtrend)
2. RSI(14) > 70 AND falling (overbought but weakening)
3. Volume > 200-period average (momentum confirmed)

### Exit Rules

| Exit Type | Condition |
|-----------|-----------|
| **Take Profit** | +4% (or +3% in volatile markets) |
| **Stop Loss** | -1% (fixed, no exceptions) |
| **Time Exit** | Close after 1 hour if TP/SL not hit |

### LLM Usage

**Once daily** (not every trade):
- Query: "Is the market trending or ranging today?"
- If **trending**: Use trend-following entries (above)
- If **ranging**: Switch to mean reversion (RSI extremes without volume filter)

---

## The Key Insight

> **Time-based exits** are the secret to high volume without bleeding fees.

Instead of holding for 4+ hours (swing trading), close after 1 hour regardless:
- Prevents holding through reversals
- Allows 10-20 trades/day
- Caps losses on bad entries
- Still captures 4% moves when they happen fast

---

## Volume vs. Profit Tradeoff

| Trades/Day | Daily Fees | Required Edge | Verdict |
|------------|------------|---------------|---------|
| 50+ | 5-7% | Impossible | ❌ |
| 20-30 | 3-4% | Very hard | ⚠️ |
| **10-20** | **1.5-3%** | **Achievable** | ✅ |
| 5-10 | 0.5-1.5% | Easy but low volume | ✅ |

**Qwen's recommendation**: 10-20 trades/day is the sweet spot.

---

## Implementation Changes Needed

### Current Bot (v5_swing_trading)
```
TAKE_PROFIT = 15%
STOP_LOSS = 5%
MIN_HOLD = 4 hours
MAX_HOLD = 96 hours
CHECK_INTERVAL = 30 minutes
```

### Qwen's High Volume Version
```
TAKE_PROFIT = 4%        # Smaller target, hit more often
STOP_LOSS = 1%          # Tighter stop, cut fast
TIME_EXIT = 1 hour      # Force close if no TP/SL
CHECK_INTERVAL = 10 min # Check more frequently
MAX_TRADES_DAY = 20     # Cap to manage fees
```

---

## Risk Management

- **Max daily risk**: 2% of capital (20 trades × 1% each)
- **Position size**: 1% of capital per trade
- **Daily cap**: Stop trading after 20 trades OR 2% drawdown

---

## What This Means

1. **50+ trades/day is a pipe dream** - fees will eat you alive
2. **10-20 trades/day IS achievable** with proper R/R (4:1)
3. **Time-based exits** are key to maintaining volume
4. **LLM should be used ONCE daily** for regime detection, not per-trade
5. **1-hour candles** are the right timeframe (not 5-min or 4-hour)

---

## Next Steps

1. Modify swing_trading_agent with Qwen's parameters
2. Add time-based exit (close after 1 hour)
3. Add daily trade cap (20 trades max)
4. Add LLM regime detection (once daily)
5. Backtest on 1-hour BTC/ETH/SOL data
6. Paper trade before going live

---

*Analysis by Qwen QwQ-32B via OpenRouter*
