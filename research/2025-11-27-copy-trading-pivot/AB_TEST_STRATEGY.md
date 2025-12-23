# A/B Test Strategy Design
## Two High-Volume Strategies for Direct Comparison

**Date**: November 27, 2025
**Status**: Ready for Testing

---

## The Experiment

We're testing TWO high-volume strategies simultaneously on different DEXs:

| DEX | Strategy | TP | SL | Max Hold | Special |
|-----|----------|----|----|----------|---------|
| **Hibachi** | TIME_CAPPED | 4% | 1% | 1 HOUR | Force close after 1hr |
| **Extended** | RUNNERS_RUN | 8% | 1% | Unlimited | Trailing stop at +2% |

---

## Why This A/B Test?

### The User's Goal
- **High volume** (many trades)
- **Profitable** (net positive)
- **Let runners run** (don't cut winners early)

### The Contradiction
Qwen analysis showed:
- 50+ trades/day = guaranteed loss (fees)
- Winning wallets hold 4+ hours (not high volume)
- Time-based exits enable more trades

### The Compromise
**Strategy A (TIME_CAPPED)**: Pure Qwen recommendation
- 1 hour max hold
- High turnover
- Many small wins/losses

**Strategy B (RUNNERS_RUN)**: User's preference
- No time limit
- Trailing stops capture big moves
- Fewer trades but bigger winners

---

## Strategy A: TIME_CAPPED (Hibachi)

```python
TAKE_PROFIT = 4%      # Exit at +4%
STOP_LOSS = 1%        # Exit at -1%
MAX_HOLD = 1 HOUR     # FORCE CLOSE regardless of P/L
TRAILING = OFF
```

### Philosophy
- High turnover, many trades
- Quick in, quick out
- Accept small wins/losses
- Never hold through reversals

### Expected Outcome
At 25% win rate (20 trades/day):
- 5 wins × +3.9% = +19.5%
- 15 losses × -1.1% = -16.5%
- **Net: +3%/day**

### Risks
- Missing big moves (closed at +4% when it went +20%)
- Over-trading in choppy markets
- Emotional frustration seeing closed trades run

---

## Strategy B: RUNNERS_RUN (Extended)

```python
TAKE_PROFIT = 8%       # Higher target
STOP_LOSS = 1%         # Same tight stop
MAX_HOLD = UNLIMITED   # Let it run
TRAILING = ON          # Activate at +2%, trail by 1.5%
```

### Philosophy
- Cut losers fast (-1%)
- Let winners run
- Trailing stop locks in profit
- Quality over quantity

### How Trailing Stop Works
1. Position opens at $100
2. Price rises to $102 (+2%) → Trailing activates
3. Trail follows 1.5% below peak
4. Price rises to $105 (+5%) → Trail at $103.50
5. Price drops to $103.50 → CLOSE (locked in +3.5%)

### Expected Outcome
Fewer trades (maybe 10/day) but higher R/R (8:1):
- 2-3 wins × +7% avg (trailing captures) = +15-20%
- 7-8 losses × -1.1% = -8%
- **Net: +7-12%/day** (but more variance)

### Risks
- Lower trade count
- Bigger individual losses if trailing never activates
- More emotional (watching position swing)

---

## Files Created

```
high_volume_agent/
├── strategies.py           # Strategy definitions
├── adaptive_exit_rules.py  # Exit logic for both
├── bot_ab_test.py         # Main A/B test bot
├── bot_high_volume.py     # Original (Strategy A only)
├── config.py              # Default config
└── high_volume_exit_rules.py
```

---

## How to Run

```bash
# Dry run (test mode)
python -m high_volume_agent.bot_ab_test --dry-run

# Live trading
python -m high_volume_agent.bot_ab_test --live

# Check logs
tail -f logs/ab_test_bot.log
```

---

## Success Metrics

Track after 1 week:

| Metric | Hibachi (A) | Extended (B) | Winner |
|--------|-------------|--------------|--------|
| Total Trades | ? | ? | Higher |
| Win Rate | ? | ? | Higher |
| Avg Win % | ? | ? | Higher |
| Avg Loss % | ? | ? | Lower (abs) |
| Net P/L % | ? | ? | Higher |
| Max Drawdown | ? | ? | Lower |

---

## Decision After Testing

**If Strategy A wins**: Focus on high turnover, tighter stops
**If Strategy B wins**: Focus on trailing stops, let runners run
**If both profitable**: Run both on different assets

---

## Key Insight

> We're testing **time-capped exits vs trailing stops** on identical markets.

This will definitively answer: Should we force close or let runners run?

---

*Based on Qwen QwQ-32B analysis + user feedback*
