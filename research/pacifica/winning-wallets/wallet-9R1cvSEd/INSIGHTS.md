# Winning Wallet Insights - Pacifica Strategy Development

**Analysis Date**: 2025-11-07
**Data Source**: 840 trade entries from wallet 9R1cvSEd
**Completed Trades Analyzed**: 184
**Total Net P&L**: $668,277.75

---

## Key Findings

### 🎯 Win Rate & Performance
- **Win Rate**: 75.5% (139 wins, 45 losses)
- **Average Winner**: $10,549.83 per trade
- **Average Loser**: -$17,715.55 per trade
- **Profit Factor**: 0.60x (winners/losers ratio)
- **Net ROI**: High absolute returns despite 0.08% round-trip fees

**Interpretation**: This wallet uses a **high win rate strategy** with large position sizes. The few losses are significantly larger than wins, but the high win rate (75.5%) more than compensates.

---

### ⏱️ Hold Time Analysis

| Category | Count | % of Trades | Win Rate |
|----------|-------|-------------|----------|
| Scalp (≤15 min) | 0 | 0% | - |
| Short Swing (15-60 min) | 0 | 0% | - |
| Medium Swing (1-4 hrs) | 18 | 9.8% | 61.1% |
| Long Swing (>4 hrs) | 166 | 90.2% | 77.1% |

**Key Metrics**:
- Average Hold Time: **93.5 hours (3.9 days)**
- Median Hold Time: **98.0 hours (4.1 days)**

**Critical Insight**:
- **NO scalping or day trading** - Zero trades under 15 minutes
- **90.2% of trades held >4 hours** (swing trading)
- **Longer holds have higher win rates** (77.1% vs 61.1%)
- Fees are only 0.1% of gross P&L because trades capture multi-day moves

**Implication for Our Bot**:
- ❌ Avoid 5-minute decision cycles with quick exits
- ✅ Target hold times of 4+ hours minimum
- ✅ Wait for high-conviction setups with larger profit targets (>1%)
- ✅ Fees become negligible on multi-day swings

---

### 💵 Position Sizing

| Metric | Value |
|--------|-------|
| Average Position | $7,914.02 |
| Median Position | $12.39 |
| Min Position | $3.96 |
| Max Position | $91,892.08 |

**Critical Observation**: Huge variance in position sizes
- Median of $12.39 suggests many small test entries
- Average of $7,914 indicates occasional LARGE positions
- Max position of $91,892 shows aggressive sizing on high-conviction trades

**Strategy Pattern Identified**:
1. Enter small ($10-50) to test the trade
2. Scale up aggressively if it moves in favor
3. Final position size varies 1,000x based on conviction

**Implication for Our Bot**:
- Current $250-500 notional ($5-10 margin @ 50x) is reasonable for initial entries
- Need to implement **position scaling** on winning trades
- Consider 2x-5x increase on trades showing >0.5% profit

---

### 🎯 Symbol Performance

| Symbol | Trades | Win Rate | Total P&L |
|--------|--------|----------|-----------|
| **PAXG** | 155 | 78.7% | $526,906.56 |
| **ZEC** | 12 | 91.7% | $274,496.92 |
| **ASTER** | 2 | 100% | $59,004.57 |
| **TAO** | 3 | 33.3% | $39,911.71 |
| ENA | 2 | 50% | -$42,123.56 |
| VIRTUAL | 2 | 50% | -$64,425.47 |
| XPL | 4 | 25% | -$113,000.72 |
| MON | 3 | 0% | -$2,608.28 |
| 2Z | 1 | 0% | -$8,935.32 |

**Key Patterns**:
- **PAXG dominance**: 84% of trades (155/184), 78.7% win rate
- **Selective altcoin trading**: Only trades alts with strong conviction
- **High variance on alts**: Either huge wins (ZEC, ASTER) or huge losses (XPL, VIRTUAL)

**Implication for Our Bot**:
- ✅ Focus on **stable, liquid markets** (PAXG = tokenized gold, very stable)
- ✅ SOL/BTC are similar to PAXG (high liquidity, lower volatility than memecoins)
- ⚠️ Be cautious with low-liquidity alts - they can move against you fast
- Consider **symbol filtering** - only trade tokens with >$10M 24h volume

---

## Actionable Strategy Changes for Pacifica Bot

### 1. Increase Minimum Hold Time Target
**Current**: 5-minute check intervals, can exit quickly
**Recommended**:
- Set minimum hold time of **4 hours** before considering exits
- Adjust profit targets to **>1%** (vs 0.1-0.5% on Lighter)
- This makes fees (0.08%) negligible relative to profit target

### 2. Implement Position Scaling
**Current**: Fixed $250-500 notional per trade
**Recommended**:
- Initial entry: $250 notional ($5 margin)
- If trade moves +0.5% in our favor: Add $250 more
- If trade moves +1.0% in our favor: Add $500 more
- Maximum position: $1,500 notional ($30 margin) per symbol

### 3. Symbol Selection Criteria
**Add these filters**:
- ✅ Minimum 24h volume: $10M
- ✅ Prefer "boring" coins (SOL, BTC, ETH) over memecoins
- ✅ Avoid tokens with <7 days of trading history
- ⚠️ Reduce max exposure on tokens with >10% daily volatility

### 4. Profit Target Adjustment
**Current**: Likely targeting small moves (0.2-0.5%)
**Recommended**:
- Minimum profit target: **1.0%** (vs 0.08% fees = 12.5x fee coverage)
- Preferred profit target: **2.0-3.0%**
- Stop loss: **-1.5%** (maintain 1.5:1 reward/risk ratio)

### 5. Entry Timing - Wait for Pullbacks
**Observation**: High win rate (75.5%) suggests good entry timing
**Hypothesis**: Wallet waits for pullbacks in uptrends rather than chasing
**Recommended**:
- Don't chase breakouts immediately
- Wait for 0.5-1% pullback before entering
- Use RSI < 40 as confirmation for long entries
- Use RSI > 60 as confirmation for short entries

---

## Comparison to Lighter Bot Strategy

| Aspect | Lighter (Zero Fees) | Pacifica (0.08% Fees) |
|--------|---------------------|----------------------|
| **Hold Time** | Minutes to hours | 4+ hours (days) |
| **Profit Target** | 0.1-0.5% | 1.0-3.0% |
| **Trade Frequency** | High (every 5 min check) | Low (selective) |
| **Position Sizing** | Fixed $5-10 margin | Scaled $5-30 margin |
| **Win Rate Required** | 50%+ | 60%+ |
| **Symbol Focus** | Any liquid market | Stable, high-volume |

**Key Takeaway**: Pacifica strategy must be **more selective, longer-term, and larger positions** to overcome fees.

---

## Implementation Priority

### 🔴 High Priority (Implement First)
1. **Increase profit targets** to 1%+ minimum
2. **Add 4-hour minimum hold time** logic
3. **Filter symbols by 24h volume** (>$10M)

### 🟡 Medium Priority (Next)
4. Implement **position scaling** on winning trades
5. Add **RSI pullback confirmation** for entries
6. Avoid **volatile memecoins** (<7 day history)

### 🟢 Low Priority (Future)
7. Advanced risk management (max drawdown limits)
8. Symbol-specific strategies (PAXG vs SOL vs BTC)
9. Correlation analysis (avoid multiple correlated longs)

---

## Expected Impact

**Before** (Current Pacifica Bot):
- Small $5-10 positions
- Fast exits (minutes to hours)
- 0.08% fees eat significant % of profit
- Risk of death by 1000 cuts

**After** (Winning Wallet Strategy):
- Larger $5-30 positions (scaled)
- Patient exits (days)
- 0.08% fees become negligible on 2-3% moves
- Higher win rate through selectivity

**Target Metrics**:
- Win rate: 65%+ (vs 50% break-even)
- Average hold time: 24+ hours
- Average profit per winner: 2%+
- Average loss per loser: -1.5%
- Profit factor: 1.5x+ (winners/losers)

---

## Next Steps

1. ✅ Review this analysis
2. ⬜ Update Pacifica bot prompt to emphasize longer holds
3. ⬜ Implement minimum profit target of 1%
4. ⬜ Add volume filtering to symbol selection
5. ⬜ Test new strategy in dry-run for 24 hours
6. ⬜ Compare results to Lighter bot performance
7. ⬜ Iterate based on results

---

**Generated by**: `analyze_wallet_trades.py`
**Files**:
- `pacifica-trade-history-9R1cvSEd-2025-11-07.csv` (raw data)
- `pacifica-trade-history-9R1cvSEd-2025-11-07_matched_trades.csv` (processed)
- `pacifica-trade-history-9R1cvSEd-2025-11-07_analysis.md` (full report)
