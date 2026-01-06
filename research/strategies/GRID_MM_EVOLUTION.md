# Grid Market Maker Strategy Evolution

**Exchange**: Paradex (ZERO maker fees, -0.005% rebate)
**Symbol**: BTC-USD-PERP
**Capital**: $1,000
**Duration**: 60 minutes per test

---

## Results Summary

| Ver | Volume | P&L | Per $10k | Change | Key Insight |
|-----|--------|-----|----------|--------|-------------|
| v1 | $1,800 | +$0.09 | +$0.48 | baseline | Low volume, barely profitable |
| v2 | $4,200 | -$0.85 | -$2.02 | -520% | More volume = more adverse selection |
| v3 | $8,500 | -$1.65 | -$1.94 | +4% | Volatility adjustment helped slightly |
| v4 | $12,800 | -$2.45 | -$1.91 | +2% | Inventory skewing marginal improvement |
| v5 | $15,600 | -$2.29 | -$1.47 | +23% | Force close at 5 bps reduced losses |
| v6 | $22,310 | -$2.81 | -$1.26 | +14% | Preemptive pausing = ZERO force closes |
| v7 | $9,180 | -$0.71 | -$0.77 | +39% | Min pause duration = best efficiency |
| **v8** | **$6,549** | **+$1.19** | **+$1.81** | **PROFIT** | **Full history context = BREAKTHROUGH** |

---

## Version Details

### v1 - Baseline (Original)
**Date**: 2026-01-05 09:33
**File**: `scripts/experiment_grid_mm.py`

**Parameters**:
- Spread: 1 bps from mid
- Grid Reset: 0.25% price movement
- Stop Loss: 10% drawdown
- Order Size: $100
- Levels: 3 per side

**Results**:
- Volume: $1,800
- Fills: 18
- P&L: +$0.09
- Per $10k: +$0.48

**Analysis**:
- Profitable but VERY low volume
- 1 bps spread too tight for real fills
- Only got fills when price moved through our levels
- Need more aggressive parameters

---

### v2 - Increased Aggression
**Date**: 2026-01-05

**Changes from v1**:
- Spread: 2.5 bps (widened for more fills)
- Order Size: $200 (doubled)
- Levels: 5 per side
- Grid Reset: 0.15% (tighter)

**Results**:
- Volume: $4,200
- P&L: -$0.85
- Per $10k: -$2.02

**Analysis**:
- More volume achieved
- BUT: Massive adverse selection
- Getting filled = wrong side of trend
- Wider spread didn't help - just delayed the inevitable
- **KEY LEARNING**: More fills != more profit

---

### v3 - Volatility-Adjusted Spread
**Date**: 2026-01-05

**Changes from v2**:
- Added volatility calculation (30-sample window)
- Spread multiplier based on volatility (1.5x)
- Dynamic spread adjustment

**Results**:
- Volume: $8,500
- P&L: -$1.65
- Per $10k: -$1.94

**Analysis**:
- Volatility adjustment helped slightly (+4%)
- Still getting killed by adverse selection
- Problem: Spread widens AFTER volatility, not BEFORE
- Need PREDICTIVE, not REACTIVE logic

---

### v4 - Inventory Skewing
**Date**: 2026-01-05

**Changes from v3**:
- Added position tracking
- Inventory skewing: reduce order size on overweight side
- Max inventory limit: 50% of capital
- Position-based grid centering

**Results**:
- Volume: $12,800
- P&L: -$2.45
- Per $10k: -$1.91

**Analysis**:
- Marginal improvement (+2%)
- Skewing reduces size but not the problem
- Still entering positions at wrong times
- Need to PREVENT bad fills, not just reduce size

---

### v5 - Force Close on Trends
**Date**: 2026-01-05

**Qwen Consultation**: First AI-assisted iteration

**Changes from v4**:
- Rate of Change (ROC) calculation: 10-second lookback
- Force close threshold: 5 bps
- Close short if ROC > +5 bps (strong uptrend)
- Close long if ROC < -5 bps (strong downtrend)

**Results**:
- Volume: $15,600
- P&L: -$2.29
- Per $10k: -$1.47
- Force closes: 4

**Analysis**:
- Significant improvement (+23%)
- Force close prevents catastrophic losses
- BUT: Force close still locks in losses
- **KEY LEARNING**: PREVENTING bad positions > cutting them early

---

### v6 - Preemptive Order Pausing
**Date**: 2026-01-05 13:46

**Qwen v6 Recommendations**:
1. PAUSE orders during trends instead of force closing after
2. ROC threshold: 2.0 bps (early detection)
3. Pause SELL in uptrends, BUY in downtrends
4. Force close threshold: 5 bps normal, 8 bps during pause
5. Keep inventory limit at 50%

**Parameters**:
- Spread: 2.5 bps
- ROC threshold: 2.0 bps
- Force close: 5 bps normal, 8 bps during pause
- Order size: $200
- Levels: 5

**Results**:
- Volume: $22,310
- Fills: 103
- P&L: -$2.81
- Per $10k: -$1.26
- Force closes: **ZERO**

**Analysis**:
- 14% improvement over v5
- ZERO force closes = preemptive pausing works
- Higher volume but still losing
- **KEY LEARNING**: Pause duration matters - need to hold pause longer

---

### v7 - Minimum Pause Duration + Tighter Controls
**Date**: 2026-01-05 14:59

**Qwen v7 Recommendations**:
1. TIGHTER spread: 1.5 bps (be MORE aggressive)
2. LOWER ROC threshold: 1.5 bps (catch trends earlier)
3. LOWER inventory limit: 30% (reduce risk)
4. TIGHTER force close: 3 bps normal, 6 bps during pause
5. Minimum pause duration: 20 seconds

**Parameters**:
- Spread: 1.5 bps
- ROC threshold: 1.5 bps
- Min pause duration: 20 seconds
- Force close: 3 bps normal, 6 bps during pause
- Inventory limit: 30%
- Order size: $200
- Levels: 5

**Results**:
- Volume: $9,180 (LOW)
- Fills: 55
- P&L: -$0.71
- Per $10k: **-$0.77** (BEST)

**Analysis**:
- 39% improvement in efficiency
- Volume dropped significantly due to aggressive pausing
- Minimum pause duration prevents re-entering too soon
- Trade-off: efficiency vs volume
- **KEY LEARNING**: Can't have both max efficiency AND max volume

---

## Key Learnings (Cumulative)

### What DOESN'T Work:
1. **Wider spreads for protection** - Just delays adverse selection
2. **Reactive volatility adjustment** - Too slow, damage already done
3. **Inventory skewing alone** - Reduces exposure but not root cause
4. **Force closing positions** - Locks in losses, reactive not proactive

### What WORKS:
1. **Preemptive order pausing** - PREVENT bad fills, don't just cut them
2. **ROC-based trend detection** - Fast, simple, effective
3. **Minimum pause duration** - Don't resume too early
4. **Tight spreads + early detection** - Be aggressive but quick to pause
5. **Low inventory limits** - Less exposure = less risk

### The Core Problem:
**Market making on a trending market = guaranteed adverse selection**

Every fill is someone trading INTO you. If price is trending:
- Buy fills = someone selling into your bid as price falls
- Sell fills = someone buying your ask as price rises

The ONLY defense is to **pause orders during trends**.

---

## Trade-offs Discovered

| Approach | Pro | Con |
|----------|-----|-----|
| Wider spread | Fewer adverse fills | Lower volume, still lose |
| Tighter spread | More volume | More adverse selection |
| Early pausing | Avoid bad fills | Miss good fills |
| Late pausing | More fills | More adverse selection |
| Long pause | Fully avoid trend | Low volume |
| Short pause | More volume | Resume too early |

**The optimal point**: Early detection (1.0-1.5 bps ROC) + medium pause (10-15s) + tight spread (1.5-2.0 bps)

---

### v8 - PROFITABLE (Full History Context)
**Date**: 2026-01-05 16:09

**Key Insight**: When Qwen was given the COMPLETE v1-v7 history, it made DIFFERENT recommendations than when given only v5-v7 context. The full history prevented recommending approaches already proven to fail (like widening spreads).

**Qwen v8 Recommendations (with full v1-v7 context)**:
1. KEEP spread tight: 1.5 bps (v2-v4 proved widening doesn't help)
2. LOWER ROC threshold: 1.0 bps (catch trends even earlier)
3. REDUCE pause duration: 15s (from 20) - balance volume/safety
4. LOWER inventory limit: 25% (from 30%) - less exposure is better
5. INCREASE order size: $250 (from $200) - more volume per fill
6. ADD level: 6 levels (from 5) - more depth

**Parameters**:
- Spread: 1.5 bps (KEPT TIGHT - key insight)
- ROC threshold: 1.0 bps
- Pause duration: 15 seconds
- Inventory limit: 25%
- Order size: $250
- Levels: 6

**Results**:
- Volume: $6,549
- Fills: 37
- P&L: **+$1.19** (POSITIVE!)
- Per $10k: **+$1.81**

**Analysis**:
- **FIRST PROFITABLE VERSION** since v1!
- Lower volume but much better efficiency
- Full history context prevented Qwen from suggesting failed approaches
- The combination of tight spread + early detection + conservative inventory = profit
- **KEY LEARNING**: AI recommendations improve dramatically with complete historical context

---

## Recommendations for v9+

Based on the full v1-v7 history:

1. **DO NOT widen spread back to 2.5 bps** - v2-v4 proved this doesn't help
2. **Keep tight spread (1.5-2.0 bps)** - This is not the problem
3. **Focus on pause timing** - This is the KEY variable
4. **ROC threshold: 1.0-1.5 bps** - Earlier is better
5. **Pause duration: 10-15 seconds** - Balance volume vs safety
6. **Inventory limit: 30-35%** - Lower is better

The goal is not to maximize volume. The goal is to maximize **profit per unit volume**.

---

## File References

- Strategy code: `scripts/grid_mm_v2.py`
- Original v1: `scripts/experiment_grid_mm.py`
- V6 results: `logs/grid_mm_v6_results.txt`
- V7 results: `logs/grid_mm_v7_results.txt`
- V1 results: `logs/grid_mm_results.txt`

---

*Last updated: 2026-01-05 16:09*
*Document for Claude/Qwen reference*
*v8 achieved PROFITABILITY - first since v1!*
