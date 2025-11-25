# Intelligent Position Sizing System

**Date**: 2025-11-06
**Status**: Ready to implement
**Goal**: Make sizing adaptive, smart, and volume-optimized

---

## Problem with Current System

**Current** (hardcoded, rigid):
```python
if confidence >= 0.8:  → $10  (2x multiplier)
elif confidence >= 0.6: → $7.50 (1.5x)
else:                  → $5  (1x)
```

**Issues**:
- ❌ Ignores momentum strength (MACD +3.2 vs +0.1 same size)
- ❌ Ignores volatility (treats BTC and DOGE same)
- ❌ Ignores setup quality (single indicator vs 4-indicator confluence)
- ❌ Can't "let runners run" (fixed size)
- ❌ No adaptation to win/loss streaks

---

## New System: Multi-Factor Adaptive Sizing

### Formula

```
Final Size = Base Position × (Confidence × Momentum × Volatility × Quality × Streak)
             └─ Capped at 0.5x-3.0x for safety
```

### Factors Explained

**1. Confidence (Base Multiplier)**
- **Purpose**: LLM confidence drives baseline size
- **Range**: 0.7x - 1.8x (adaptive mode)
- **Example**:
  - 0.85+ confidence = 1.8x base
  - 0.7-0.85 = 1.4x base
  - 0.5-0.7 = 1.0x base
  - <0.5 = 0.7x base

**2. Momentum Adjustment**
- **Purpose**: Reward strong MACD (let runners run!)
- **Range**: 0.9x - 1.25x
- **Example**:
  - MACD +3.2 (very strong) = 1.25x → **+25% size**
  - MACD +0.8 (strong) = 1.15x → +15% size
  - MACD +0.2 (moderate) = 1.0x
  - MACD +0.05 (weak) = 0.9x → -10% size

**3. Volatility Adjustment**
- **Purpose**: Reduce size in choppy markets (risk management)
- **Range**: 0.7x - 1.2x
- **Example**:
  - ATR 1.5% (low vol) = 1.2x → **+20% size** (safe to size up)
  - ATR 3% (normal) = 1.0x
  - ATR 6% (high vol) = 0.85x → -15% size
  - ATR 9% (extreme) = 0.7x → -30% size

**4. Setup Quality Adjustment**
- **Purpose**: Reward high-confidence setups with indicator confluence
- **Range**: 1.0x - 1.2x
- **Example**:
  - 4/4 indicators aligned + V2 citations = 1.26x → **+26% size**
  - 3/4 indicators aligned = 1.2x → +20% size
  - 2/4 indicators aligned = 1.1x → +10% size
  - 1/4 indicators = 1.0x

**5. Streak Adjustment**
- **Purpose**: Build on wins, reduce after losses
- **Range**: 0.85x - 1.1x
- **Example**:
  - 3+ wins in a row = 1.1x → **+10% size**
  - 2 wins = 1.05x → +5% size
  - Neutral = 1.0x
  - 2 losses = 0.92x → -8% size
  - 3+ losses = 0.85x → -15% size

---

## Example Sizing Calculations

### Example 1: Strong Setup (High Volume Target)

**Setup**:
- Confidence: 0.88 (very high)
- MACD: +2.1 (very strong momentum)
- ATR: 2.3% (low volatility)
- Indicators: 4/4 aligned (RSI oversold, MACD bullish, Stoch oversold, ADX strong)
- Streak: 3 wins

**Calculation**:
```
Base position = $107 * 0.85 / 15 = $6.05

Multipliers:
- Confidence: 1.8x (0.88 confidence)
- Momentum: 1.25x (MACD +2.1)
- Volatility: 1.2x (ATR 2.3%)
- Quality: 1.26x (4/4 indicators + V2 citations)
- Streak: 1.1x (3 wins)

Total multiplier = 1.8 × 1.25 × 1.2 × 1.26 × 1.1 = 3.75x
Capped at 3.0x (safety limit)

Final size = $6.05 × 3.0 = $18.15
```

**Result**: $18.15 position (vs current $10) → **+82% more volume on best setups!**

---

### Example 2: Weak Setup (Risk Management)

**Setup**:
- Confidence: 0.62 (moderate)
- MACD: +0.08 (weak momentum)
- ATR: 7.5% (high volatility)
- Indicators: 1/4 aligned (only RSI, others mixed)
- Streak: 2 losses

**Calculation**:
```
Base position = $6.05

Multipliers:
- Confidence: 1.0x (0.62 confidence)
- Momentum: 0.9x (MACD +0.08 weak)
- Volatility: 0.7x (ATR 7.5% extreme)
- Quality: 1.0x (1/4 indicators)
- Streak: 0.92x (2 losses)

Total multiplier = 1.0 × 0.9 × 0.7 × 1.0 × 0.92 = 0.58x

Final size = $6.05 × 0.58 = $3.51
Apply minimum = $10 (exchange requirement)
```

**Result**: $10 position (minimum enforced) - system wants $3.51, but can't go below $10

---

### Example 3: Balanced Setup

**Setup**:
- Confidence: 0.75 (good)
- MACD: +0.6 (strong)
- ATR: 3.2% (normal)
- Indicators: 3/4 aligned (good confluence)
- Streak: neutral

**Calculation**:
```
Base position = $6.05

Multipliers:
- Confidence: 1.4x (0.75 confidence)
- Momentum: 1.15x (MACD +0.6)
- Volatility: 1.0x (ATR 3.2%)
- Quality: 1.2x (3/4 indicators)
- Streak: 1.0x (neutral)

Total multiplier = 1.4 × 1.15 × 1.0 × 1.2 × 1.0 = 1.93x

Final size = $6.05 × 1.93 = $11.68
```

**Result**: $11.68 position (vs current $10) → **+17% on solid setups**

---

## Sizing Modes Comparison

| Mode | Confidence Range | Max Multiplier | Best For |
|------|-----------------|----------------|----------|
| **Conservative** | 0.6x-1.2x | 2.0x | Small accounts, risk-averse |
| **Balanced** | 0.7x-1.7x | 2.5x | Default recommended |
| **Aggressive** | 0.5x-2.2x | 3.0x | Larger accounts, volume focus |
| **Adaptive** | 0.7x-1.8x + dynamic | 3.0x | Best for varying conditions |

---

## Configuration (Super Easy)

Edit `config/position_sizing_config.py`:

```python
# Quick preset selection
ACTIVE_PRESET = "volume_focused"  # or "balanced_scalping", "risk_managed"

# Or custom tuning
SIZING_MODE = "adaptive"  # "conservative", "balanced", "aggressive"
RESERVE_PERCENTAGE = 0.15  # 15% held back
MAX_POSITIONS = 15
```

**Presets**:

1. **`volume_focused`** (maximize volume):
   - Mode: aggressive
   - Reserve: 10% (more capital deployed)
   - Max positions: 12 (larger each)
   - Result: **$5-$20 per trade** (vs current $10)

2. **`balanced_scalping`** (default):
   - Mode: adaptive
   - Reserve: 15%
   - Max positions: 15
   - Result: **$10-$18 per trade**

3. **`risk_managed`** (conservative):
   - Mode: conservative
   - Reserve: 20% (higher safety buffer)
   - Max positions: 20 (more diversification)
   - Result: **$10-$12 per trade**

---

## Integration Steps

### 1. Enable in `lighter_executor.py`

Replace lines 170-244 with:

```python
from lighter_agent.execution.position_sizing import PositionSizer
from config import position_sizing_config

# Initialize sizer (once in __init__)
cfg = position_sizing_config.get_active_config()
self.sizer = PositionSizer(
    account_balance=account_balance,
    max_positions=cfg['max_positions'],
    reserve_pct=cfg['reserve_pct'],
    min_size_usd=cfg['min_usd'],
    sizing_mode=cfg['mode']
)

# Calculate size (in execute_decision)
sizing_result = self.sizer.calculate_position_size(
    confidence=confidence,
    symbol=symbol,
    market_data={
        'rsi_5m': decision.get('rsi'),
        'macd_5m': decision.get('macd'),
        'stoch_k': decision.get('stoch_k'),
        'adx_4h': decision.get('adx_4h'),
        'atr_4h': decision.get('atr_4h'),
        'current_price': decision.get('current_price')
    },
    decision_reasoning=decision.get('reason')
)

position_size_usd = sizing_result['size_usd']
logger.info(f"💰 {sizing_result['reasoning']}")
```

### 2. Update LLM decision to pass market data

In `bot_lighter.py`, add market indicators to decisions:

```python
decisions = [{
    'symbol': symbol,
    'action': action,
    'confidence': confidence,
    'reason': reason,
    'current_price': market_data.get('current_price'),
    'rsi': market_data.get('rsi_5m'),
    'macd': market_data.get('macd_5m'),
    'stoch_k': market_data.get('stoch_k'),
    'adx_4h': market_data.get('adx_4h'),
    'atr_4h': market_data.get('atr_4h')
}]
```

---

## Testing Plan

### Phase 1: Dry-Run Comparison (3 cycles)

```bash
# Test with current sizing
python3 -m lighter_agent.bot_lighter --dry-run --interval 300

# Enable intelligent sizing
# (add USE_INTELLIGENT_SIZING = True flag)

# Compare position sizes and reasoning
```

### Phase 2: Live A/B Test (24 hours)

- Hour 1-12: Current sizing
- Hour 13-24: Intelligent sizing
- Compare:
  - Average position size
  - Volume executed
  - Win rate (does quality adjustment help?)
  - P&L

### Phase 3: Optimize Thresholds

Based on results, tune:
- MACD thresholds (currently 0.1, 0.5, 1.5)
- ATR% thresholds (currently 2%, 4%, 7%)
- Multiplier ranges

---

## Expected Results

### Current Baseline

- Account: $107
- Position sizes: Mostly $10 (exchange minimum)
- Volume per cycle: $10-30 (1-3 positions)

### With Intelligent Sizing

**Best setups** (high conf + strong momentum + low vol):
- Size: $15-$18 → **+50-80% more volume**
- Let strong runners run with larger capital

**Weak setups** (low conf + weak momentum + high vol):
- Size: System wants $3-5 but hits $10 minimum → **Same as current**
- Risk management prevents oversizing

**Net effect**:
- ✅ **+40-60% more volume** on average (more high-quality entries)
- ✅ Better risk-adjusted returns (size down in chop, size up in trends)
- ✅ Adaptive to market conditions (not fixed sizing)

---

## Future Enhancements

### 1. Trailing Stops (Let Runners Run)

```python
ENABLE_TRAILING_STOPS = True
TRAILING_STOP_ACTIVATION = 1.5  # Start at +1.5%
TRAILING_STOP_DISTANCE = 0.8    # Trail 0.8% below peak
```

**Example**:
- Enter: $100
- Price hits $101.50 (+1.5%) → activate trailing stop at $100.70
- Price runs to $103 → trail stop moves to $102.18
- Price drops to $102.18 → exit with +2.18% (vs fixed 2% target)

### 2. Partial Exits (Collect Gains + Let Winners Run)

```python
ENABLE_PARTIAL_EXITS = True
PARTIAL_EXIT_LEVELS = [
    {"profit_pct": 2.0, "close_pct": 0.3},  # Take 30% at +2%
    {"profit_pct": 4.0, "close_pct": 0.5},  # Take 50% more at +4%
]
```

**Example**:
- Enter 10 units at $100
- Hits $102 (+2%) → close 3 units, keep 7 running
- Hits $104 (+4%) → close 3.5 more units, keep 3.5 running
- Remaining 3.5 units ride until stop or target

### 3. Volatility Breakout Sizing

Size up on volatility contractions (squeeze setups):
```python
if atr_pct < 1.5 and atr_declining:
    # Volatility squeeze → increase size before breakout
    volatility_adj = 1.3
```

---

## Key Takeaways

1. **Current system is too rigid** - treats all 0.8+ confidence setups the same ($10)
2. **New system is adaptive** - considers 5 factors (confidence, momentum, vol, quality, streak)
3. **Configuration is simple** - just change preset or tune a few numbers
4. **Volume increases 40-60%** - larger sizes on best setups
5. **Risk is managed** - smaller sizes in chop, safety caps
6. **Easy to test** - dry-run compare, then A/B test live
7. **Future-proof** - trailing stops and partial exits ready to enable

**Bottom line**: Smarter sizing = more volume on winners, less risk on losers.
