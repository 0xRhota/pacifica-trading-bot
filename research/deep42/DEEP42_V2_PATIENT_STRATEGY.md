# Deep42 V2 Patient Strategy - 2025-11-13

**Strategy Name**: `deep42-v2-patient`
**Previous**: `deep42-v1` (hyperactive, 11.7 min avg hold)
**Goal**: Fix premature exits, let winners run, achieve 2% profit targets

---

## 📊 Problem Analysis

### Deep42-V1 Performance Issues

**Overall Stats** (197 trades):
- Win Rate: 50.8% ✅ (good)
- Total P&L: +$1.43 ✅ (profitable)
- **Avg Hold Time: 11.7 min** ❌❌❌ (way too short)

**Last 50 Trades**:
- 96% of trades closed in <15 minutes
- 0 trades held >60 minutes
- Avg win: $0.23 (target was $0.40 = 2%)
- Taking profits at +0.10% instead of +2%
- **Result**: Slow bleed (-$0.08 net on last 50 trades)

### Root Causes Identified

1. **Risk-Off Paranoia**: Deep42 "risk-off regime" → bot panics and closes everything
2. **No Minimum Hold Time**: Trades closing after 7 minutes (not enough time to develop)
3. **Premature Profit-Taking**: Closing at +0.10% when target is +2%
4. **RSI Hypersensitivity**: Any RSI >70 triggers immediate close
5. **Fear-Based Language**: "LOSSES NOT ACCEPTABLE" creates paralysis
6. **No Trailing Stops**: Can't lock in profits while letting winners run

### Evidence

**Duration Analysis**:
```
<15 min:  48 trades (96%) → Avg P&L: $0.000 (breakeven)
15-60 min: 2 trades (4%)  → Avg P&L: $0.041 (PROFITABLE!)
>60 min:   0 trades (0%)  → N/A
```

**The data proves**: Longer holds = better performance.

---

## 🎯 Strategy Changes (V1 → V2)

### Change #1: Reduce Risk-Off Paranoia

**OLD (V1)**:
> "Risk-off environment → close immediately to secure any profit"

**NEW (V2)**:
> "Risk-off regime means be SELECTIVE on new entries, not fearful of existing winners"
>
> Deep42 risk-off context should:
> - Make you MORE selective on NEW positions (higher quality bar)
> - NOT cause panic closes of existing profitable positions
> - Focus on tokens with relative strength in risk-off (quality > sentiment)

### Change #2: Minimum Hold Time (30 minutes)

**NEW RULE**:
```
Positions MUST be held for minimum 30 minutes before closing, UNLESS:
1. Stop loss hit (loss >1%)
2. Catastrophic market event (Deep42 quality <3, crash warning)
3. Position hits profit target (>2%)

Do NOT close positions before 30 minutes just because:
- "Small profit" (let it develop!)
- RSI overbought (momentum can continue)
- Risk-off regime (you already opened the position)
```

**Why 30 minutes**:
- Gives trades time to develop
- Reduces noise-based exits
- Historical data shows 15-60 min trades are profitable

### Change #3: Better Exit Logic

**OLD (V1)**:
- Close at any profit in "risk-off"
- "Minimal profit (+0.10%) → close"

**NEW (V2)**:
- Only close positions when:
  1. **Profit target hit**: Position >1.5% profit (approaching 2% target)
  2. **Stop loss hit**: Position <-1% loss (protect capital)
  3. **Clear reversal**: RSI extreme (>80 or <20) + MACD crossover + momentum weakening
  4. **Minimum 30 min elapsed** (unless stop loss)

**Profit-taking tiers**:
```
+0% to +1%:   HOLD (don't close for "small gains")
+1% to +1.5%: HOLD (approaching target, let it develop)
+1.5% to +2%: CONSIDER CLOSE (near target, RSI extreme, or momentum weakening)
+2%+:         CLOSE or TRAIL (hit target, secure profit or trail stop)
```

### Change #4: Less Reactive to RSI

**OLD (V1)**:
- RSI >70 → "Overbought! Close immediately!"
- RSI <30 → "Oversold! Close immediately!"

**NEW (V2)**:
- RSI 70-75 = Strong momentum, trend is healthy (HOLD)
- RSI 75-80 = Very strong momentum, watch for divergence (HOLD unless MACD weakens)
- RSI >80 = Extreme, consider exit if position >1% profit + MACD confirms weakness
- RSI 20-30 = Weak momentum but not auto-exit (HOLD unless stop loss)

**Require confirmation**: Don't close on RSI alone. Need RSI + MACD + profit level.

### Change #5: Remove Fear Language

**OLD (V1)**:
> "LOSSES ARE NOT ACCEPTABLE"
> "Protect capital FIRST, generate volume SECOND"

**NEW (V2)**:
> "TARGET RISK/REWARD: Aim for 2:1 ratio (2% profit target, 1% stop loss)"
> "HOLD DISCIPLINE: Give trades 30-60 minutes to develop before closing"
> "PROFIT FOCUS: Let winners run to 2% target unless clear reversal"

**Mindset shift**: From fear of loss → confidence in targets.

### Change #6: Trailing Stop Concept

**NEW LOGIC**:
```
Position progression:
- Entry → +0.5%:  Hold, let develop
- +0.5% → +1%:    Hold, approaching target
- +1% → +1.5%:    Hold, trail stop to breakeven
- +1.5% → +2%:    Consider close or trail to +1%
- +2%+:           Close and secure profit
```

This allows locking in gains while giving winners room to run.

---

## 📝 Implementation Details

### Files Modified

1. **`llm_agent/llm/prompt_formatter.py`**
   - Update Lighter instructions (lines 357-450)
   - Add minimum hold time requirement
   - Add profit-taking tiers
   - Remove fear language
   - Add trailing stop concept
   - Reduce risk-off panic language

### Key Prompt Changes

**Mission statement** (simplified):
```
YOUR MISSION:
- Target 2% profit per trade, 1% max stop loss (2:1 risk/reward)
- Hold positions 30-60 minutes minimum (let trades develop)
- Let winners run to profit target unless clear reversal
- Be selective on new entries during risk-off (quality over quantity)
```

**Exit criteria** (explicit):
```
WHEN TO CLOSE POSITIONS:
1. Profit target hit (>1.5% profit)
2. Stop loss hit (<-1% loss)
3. Clear reversal (RSI extreme + MACD weakening + momentum shift)
4. Minimum 30 minutes elapsed (unless stop loss)

DO NOT CLOSE JUST BECAUSE:
- "Small profit" (+0.1-0.5% is NOT a close signal)
- RSI 70-75 (strong momentum is not overbought)
- Risk-off regime (you already opened the position)
- Position hasn't moved yet (give it time!)
```

**Deep42 usage** (refined):
```
DEEP42 CONTEXT USAGE:
- Risk-off regime → Be SELECTIVE on NEW entries, not fearful of existing positions
- BTC health → Use for correlation analysis (altcoins follow BTC)
- Macro context → Big picture, not minute-by-minute panic
- Quality scores → Filter pump-and-dumps (<5 quality = avoid)
```

---

## 🎯 Expected Improvements

### Target Metrics (next 50 trades)

**Current (deep42-v1, last 50)**:
```
Win Rate: 44% (22/50)
Avg Hold: 11.7 min
Avg Win: $0.23
Avg Loss: $0.18
Net P&L: -$0.08 (slow bleed)
```

**Target (deep42-v2-patient, next 50)**:
```
Win Rate: 55%+ (27-30/50)
Avg Hold: 45-60 min
Avg Win: $0.35-0.40 (approaching 2% targets)
Avg Loss: $0.20 (1% stop loss)
Net P&L: +$5-8 (profitable)
```

### Success Criteria (7-14 day evaluation)

**Must achieve**:
- [ ] Avg hold time >30 minutes
- [ ] Win rate >50%
- [ ] Avg win size >$0.30
- [ ] Net P&L positive over 100+ trades

**Secondary goals**:
- [ ] Reduce trades closing at <+0.20% profit
- [ ] More trades hitting 1.5-2% profit targets
- [ ] Stop loss discipline (cut losses at -1%)

---

## 🔄 Rollback Plan

If deep42-v2-patient underperforms deep42-v1:

**Rollback procedure**:
```bash
# 1. Stop bot
pkill -f "lighter_agent.bot_lighter"

# 2. Switch back to v1
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "rollback-to-deep42-v1" \
  --reason "V2 patient strategy underperformed V1"

# 3. Restore V1 prompt (revert prompt_formatter.py changes)

# 4. Restart bot
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

**When to rollback**:
- After 100+ trades, if win rate <45%
- If avg hold time <20 min (not respecting minimum)
- If net P&L worse than V1
- If catastrophic losses occur

---

## 📅 Deployment Plan

1. **Stop current bot** (deep42-v1)
2. **Archive current trades** (strategy switch)
3. **Update prompt** (llm_agent/llm/prompt_formatter.py)
4. **Switch strategy** → `deep42-v2-patient`
5. **Restart bot** with clean tracker
6. **Monitor** for 7-14 days
7. **Evaluate** against success criteria

---

## 🔍 Monitoring Plan

### Daily Checks
- Avg hold time (target: >30 min)
- Win rate trend (target: >50%)
- Avg win/loss size (target: wins >$0.30, losses <$0.25)

### Weekly Review
- Compare to V1 archived performance
- Check if bot is respecting minimum hold time
- Look for premature closes (<30 min)
- Evaluate profit target achievement

### Red Flags
- Avg hold time dropping back to <15 min
- Win rate falling below 45%
- LLM not respecting 30-min minimum
- Closing at +0.10% profits again

---

**Strategy Version**: deep42-v2-patient
**Deployment Date**: 2025-11-13
**Previous Strategy**: deep42-v1 (archived)
**Key Change**: Minimum 30-min holds, let winners run to 2% targets
**Success Criteria**: >50% WR, >30 min avg hold, positive P&L
