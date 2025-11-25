# Technicals-Only V1 Strategy - 2025-11-14

**Strategy Name**: `technicals-only-v1`
**Previous**: `deep42-v2-patient` (Deep42 fear causing premature exits)
**Goal**: Remove Deep42 "risk-off" panic, focus purely on technical signals

---

## 📊 Problem Analysis

### Deep42-V2-Patient Issues

**Performance** (37 trades):
- Win Rate: 51.4% ✅ (decent)
- Total P&L: $0.05 ❌ (basically breakeven)
- Avg Win: $0.04 ❌ (terrible - target was $0.35)
- Risk/Reward: 1.02:1 ❌ (target was 2:1)

**Root Cause**: Deep42 "risk-off regime" panic
- **96.8% of exits** (60/62) mentioned "risk-off" or "fear"
- Closing at +0.36%, +0.26%, +0.20% profit due to "risk-off"
- **Lost profit: $15.64** if positions held to 2% targets

**Evidence**:
```
Example exits:
- XMR: +0.36% - "closing due to risk-off regime"
- APT: +0.26% - "risk-off regime suggests taking profits"
- TAO: +0.20% - "risk-off environment with BTC neutral"
```

Deep42 was supposed to help filter bad trades, but instead it's causing panic sells of GOOD trades.

---

## 🎯 Technicals-Only Strategy

### Core Principle

**ONLY use technical indicators for decisions. NO macro sentiment, NO "risk-off regime," NO fear-based exits.**

**Available Technical Data**:
- **5-minute indicators**: RSI, MACD, EMA20, Bollinger Bands, Stochastic
- **4-hour indicators**: EMA20, ATR, ADX (trend strength)
- **Market data**: Price, Volume (24h), Funding Rates, Open Interest
- **Multi-timeframe**: 5-min for timing, 4h for trend context

**The LLM is STILL valuable for**:
- Synthesizing 10+ indicators simultaneously
- Recognizing complex technical patterns (RSI divergence, MACD crossover confirmations)
- Adaptive learning (what works, what doesn't)
- Clear reasoning for every trade

---

## 📋 Entry Rules

### Long Entry Requirements

**ALL of these must be true**:
1. **RSI > 50** (momentum building, not oversold bounce)
2. **MACD positive AND rising** (bullish momentum confirmed)
3. **Price > EMA20 (5-min)** (short-term uptrend)
4. **4h ADX > 25** (strong trend, not choppy)
5. **Volume > 10M USD** (sufficient liquidity)
6. **Stochastic %K > 50** (momentum present)

**Optional enhancers** (increase confidence):
- Price breaking above Bollinger Band middle
- Funding rate negative (shorts paying longs)
- Open Interest increasing (new money entering)

### Short Entry Requirements

**ALL of these must be true**:
1. **RSI < 50** (downward momentum)
2. **MACD negative AND falling** (bearish momentum)
3. **Price < EMA20 (5-min)** (short-term downtrend)
4. **4h ADX > 25** (strong trend)
5. **Volume > 10M USD**
6. **Stochastic %K < 50** (downward momentum)

---

## 📋 Exit Rules

### Profit Target Exits

**Close position when**:
- **Position ≥ +2%** → CLOSE (target achieved)
- **Position ≥ +1.5% AND technical reversal** → CLOSE
  - Technical reversal = RSI extreme (>80 or <20) + MACD crossover + momentum weakening

**DO NOT close just because**:
- Position at +0.1%, +0.3%, +0.5% profit (LET IT RUN!)
- RSI 70-75 (strong momentum, not overbought yet)
- Some news headline or "market sentiment"

### Stop Loss Exits

**Close position when**:
- **Position ≤ -1%** → CLOSE (stop loss hit)
- **Clear technical breakdown**:
  - MACD crosses negative (momentum reversal)
  - Price breaks below EMA20 with high volume
  - RSI drops below 40 on longs (or above 60 on shorts)

### Time-Based Rules

**Minimum hold time: 30 minutes**
- UNLESS: Stop loss hit (<-1%) or profit target hit (>2%)
- Prevents noise-based exits
- Gives trades time to develop

**Position tiers**:
```
Entry → +0.5%:  HOLD (let develop)
+0.5% → +1%:    HOLD (approaching target)
+1% → +1.5%:    HOLD + trail stop to breakeven
+1.5% → +2%:    CONSIDER CLOSE if RSI >80 + MACD weakening
+2%+:           CLOSE (target achieved)
```

---

## 🚫 What We're REMOVING

**NO MORE**:
- ❌ "Risk-off regime" mentions
- ❌ "Extreme Fear (16/100)" panic
- ❌ "Deep42 shows..." anything
- ❌ "Market sentiment" overriding technicals
- ❌ "BTC health bearish" as exit reason (unless BTC technicals show clear breakdown)
- ❌ Closing at +0.3% profit because "better to secure small gains in risk-off"

**What this means**:
- If RSI is 65, MACD positive, price above EMA20 → **HOLD** (don't close for "risk-off fear")
- If position is at +0.5% and technicals still bullish → **HOLD** (don't take tiny profit)
- Only exit when **TECHNICALS** say exit OR 2% target hit

---

## 🎯 Expected Improvements

### Target Metrics (next 50 trades)

| Metric | Deep42-V2 | Technicals Target |
|--------|-----------|-------------------|
| Win Rate | 51.4% | 55%+ |
| Avg Win | **$0.04** | **$0.30-0.40** |
| Avg Loss | $0.04 | $0.20 |
| Risk/Reward | **1.02:1** | **2:1** |
| Avg Hold | 35 min | 45-60 min |
| Net P&L (50 trades) | ~$0 | **+$5-8** |

**Key improvement**: Letting winners run to 2% target instead of closing at +0.3% for "risk-off fear"

---

## 📝 Prompt Changes

### Mission Statement (Simplified)

**OLD (Deep42-V2)**:
```
- Be selective on new entries during risk-off (quality over quantity)
- Deep42 risk-off context should make you SELECTIVE...
```

**NEW (Technicals-Only)**:
```
YOUR MISSION:
- Target 2% profit per trade, 1% max stop loss (2:1 risk/reward)
- Hold positions 30-60 minutes (let trades develop)
- Let winners run to 2% target based on TECHNICALS ONLY
- Quality over quantity - only trade clear technical setups
```

### Data Available

**REMOVE**: Deep42 sections entirely

**KEEP**:
- 5-minute indicators (RSI, MACD, EMA, Bollinger, Stochastic)
- 4-hour indicators (EMA, ATR, ADX)
- Market data (Price, Volume, Funding, OI)

### Exit Criteria

**OLD**:
```
Risk-off regime → close at small profits
Deep42 quality <3 → catastrophic event
```

**NEW**:
```
WHEN TO CLOSE:
1. Profit target hit (≥2%)
2. Stop loss hit (≤-1%)
3. Technical reversal (RSI extreme + MACD crossover + momentum weak)
4. Minimum 30 minutes elapsed (unless stop/target)

DO NOT CLOSE JUST BECAUSE:
- Small profit (+0.1-0.5%)
- RSI 70-75 (strong momentum can continue)
- Position hasn't moved yet (give it time!)
```

---

## 🔄 Deployment Plan

1. **Stop bot**
2. **Clean strategy switch** → `technicals-only-v1`
3. **Update prompt** (remove ALL Deep42 references)
4. **Restart bot**
5. **Monitor 50-100 trades**
6. **Compare to Deep42-V2**

---

## 📊 Success Criteria (50-100 trades)

**Must achieve**:
- [ ] Avg win >$0.25 (10x improvement over V2's $0.04)
- [ ] Risk/Reward >1.5:1 (vs V2's 1.02:1)
- [ ] Net P&L positive >$5 (vs V2's breakeven)
- [ ] Less than 30% of wins are "tiny" (<$0.10)

**Secondary goals**:
- [ ] Avg hold time 45+ minutes
- [ ] Win rate 55%+
- [ ] No exits mentioning "risk-off" or "fear"

---

## 🔍 Monitoring

**Daily checks**:
- Are positions hitting 2% targets?
- Is bot closing at tiny profits (+0.1-0.5%)?
- Are exit reasons purely technical?

**Red flags**:
- Wins still averaging <$0.10
- Bot somehow inventing "fear" reasons without Deep42
- Win rate dropping below 50%

---

## 🔄 Rollback Plan

If technicals-only underperforms Deep42-V2:

```bash
# Revert to Deep42-V2-Patient
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "rollback-to-deep42-v2" \
  --reason "Technicals-only underperformed"
```

**When to rollback**:
- After 100 trades, if avg win still <$0.10
- If net P&L worse than Deep42-V2
- If win rate <45%

---

**Strategy**: technicals-only-v1
**Deployment**: 2025-11-14
**Key Change**: Remove ALL Deep42 / macro sentiment / "risk-off" references
**Goal**: Let technical signals drive decisions, let winners run to 2% targets
**Expected**: 10x improvement in avg win size ($0.04 → $0.30+)
