# Strategy Management System

Simple, elegant workflow for creating, testing, and switching trading strategies.

---

## Quick Reference

```bash
# List available strategies
ls strategies/*.py

# Test new strategy
python3 -c "from pacifica.strategies.your_strategy import YourStrategy; s = YourStrategy(); print('✅ Strategy loads')"

# Switch strategy (edit config.py)
PACIFICA_STRATEGY = "long_short"  # or "vwap", "basic_long_only"
LIGHTER_STRATEGY = "vwap"         # or "long_short", "basic_long_only"

# Restart bots
pkill -f pacifica && pkill -f lighter
python3 bots/live_pacifica.py &
python3 bots/vwap_lighter_bot.py &
```

---

## Strategy Lifecycle

### 1. Create New Strategy

**File**: `strategies/my_new_strategy.py`

```python
from strategies.base_strategy import BaseStrategy

class MyNewStrategy(BaseStrategy):
    """
    Brief description of what this strategy does
    """

    def should_open_position(self, symbol: str, market_data: dict) -> tuple:
        """
        Decide if/when to open position

        Returns:
            (should_open, direction, reason)
            direction: "long" or "short" or None
        """
        # Your logic here
        return (False, None, "Not implemented yet")

    def should_close_position(self, position: dict, market_data: dict) -> tuple:
        """
        Decide when to close position

        Returns:
            (should_close, reason)
        """
        # Your logic here
        return (False, None)

    def get_position_size(self, symbol: str, price: float, balance: float) -> float:
        """
        Calculate position size

        Returns:
            size in base units (e.g. 0.05 SOL)
        """
        # Your logic here
        return 0.0
```

### 2. Document Strategy

Add to `strategies/README.md`:

```markdown
### My New Strategy
**File**: `my_new_strategy.py`
**Status**: 🚧 Development

**Entry Logic**:
- Describe entry conditions

**Exit Logic**:
- Describe exit conditions

**Position Sizing**: Fixed/Dynamic
**Expected Win Rate**: X%
**Risk/Reward**: X:1
```

### 3. Test Strategy

**Option A: Dry Run (No Orders)**
```python
# test_my_strategy.py
from strategies.my_new_strategy import MyNewStrategy
from pacifica_bot import PacificaAPI

api = PacificaAPI()
strategy = MyNewStrategy()

# Test on live market data (no orders)
for symbol in ["SOL", "ETH"]:
    market = api.get_market_data(symbol)
    should_open, direction, reason = strategy.should_open_position(symbol, market)
    print(f"{symbol}: {should_open} | {direction} | {reason}")
```

**Option B: Backtest (Future)**
```bash
python3 scripts/backtest.py --strategy my_new_strategy --days 30
```

### 4. Switch Strategy

**Edit `config.py`**:
```python
class BotConfig:
    # Strategy selection
    ACTIVE_STRATEGY = "my_new_strategy"  # Change this line
```

**Or use environment variable** (recommended):
```bash
# .env
PACIFICA_STRATEGY=my_new_strategy
LIGHTER_STRATEGY=vwap
```

**Restart bot**:
```bash
pkill -f live_pacifica
python3 bots/live_pacifica.py &
```

### 5. Monitor Performance

```bash
# View live logs
tail -f logs/pacifica.log

# View trade stats
python3 -c "from pacifica.core import pacifica_tracker; pacifica_tracker.print_stats()"

# Health check
python3 monitor.py
```

### 6. Archive Old Strategy

When replacing:
```bash
# Move to archive with timestamp
mv strategies/old_strategy.py archive/strategies/2025-01-07_old_strategy.py

# Update strategies/README.md
# Mark as "📦 Archived"
```

---

## Strategy Naming Convention

**File**: `strategies/<name>_strategy.py` or `strategies/<name>.py`

**Class**: `<Name>Strategy`

**Examples**:
- `vwap_strategy.py` → `VWAPStrategy`
- `long_short.py` → `LongShortStrategy`
- `mean_reversion.py` → `MeanReversionStrategy`

---

## Strategy Configuration

### Per-Strategy Settings

Store in strategy class:
```python
class MyStrategy(BaseStrategy):
    # Strategy-specific config
    THRESHOLD = 0.02
    LOOKBACK_PERIODS = 20
    MIN_VOLUME = 1000
```

### Global Settings

Store in `config.py`:
```python
class BotConfig:
    # Applied to all strategies
    MAX_POSITION_USD = 40.0
    STOP_LOSS = 0.01
    CHECK_FREQUENCY_SEC = 45
```

---

## Multi-DEX Strategy Matrix

Current setup:

| DEX | Strategy | Why |
|-----|----------|-----|
| Pacifica | Orderbook Imbalance | Real-time orderbook data available |
| Lighter | VWAP Mean Reversion | Zero fees enable tighter stops |

To change:

**Option 1: Different strategies per DEX**
```python
# config.py
PACIFICA_STRATEGY = "long_short"
LIGHTER_STRATEGY = "vwap"
```

**Option 2: Same strategy, different params**
```python
# In strategy file
class VWAPStrategy(BaseStrategy):
    def __init__(self, dex="pacifica"):
        if dex == "lighter":
            self.DEVIATION_THRESHOLD = 0.003  # Tighter for zero fees
        else:
            self.DEVIATION_THRESHOLD = 0.005  # Wider for fees
```

---

## Strategy Versioning

Use git tags:
```bash
# Tag successful strategy
git tag -a strat-vwap-v1.0 -m "VWAP strategy - 55% win rate"
git push --tags

# Rollback to previous version
git checkout strat-vwap-v1.0 -- strategies/vwap_strategy.py
```

---

## Strategy Development Checklist

Before going live:

- [ ] Inherits from `BaseStrategy`
- [ ] All 3 methods implemented (`should_open_position`, `should_close_position`, `get_position_size`)
- [ ] Documented in `strategies/README.md`
- [ ] Tested with dry run
- [ ] Risk parameters defined (stop loss, take profit)
- [ ] Position sizing logic validated
- [ ] Error handling for missing data
- [ ] Logged to `strategies/` git folder
- [ ] Small position test on live ($10-20)
- [ ] Performance monitored for 24h minimum

---

## Quick Strategy Comparison

| Strategy | Win Rate | R:R | Check Freq | Best For |
|----------|----------|-----|------------|----------|
| VWAP Mean Reversion | 55-65% | 3:1 | 5 min | Ranging markets, zero fees |
| Orderbook Imbalance | 45-55% | 2:1 | 15 min | Trending markets |
| Basic Long Only | 30-40% | 1:2 | 15 min | Bull markets |

---

## Troubleshooting

**Strategy not loading?**
```bash
# Check syntax
python3 -c "from strategies.my_strategy import MyStrategy"

# Check base class
grep "BaseStrategy" strategies/my_strategy.py
```

**Bot using wrong strategy?**
```bash
# Check config
grep ACTIVE_STRATEGY config.py

# Check bot startup logs
tail logs/pacifica.log | grep -i strategy
```

**Strategy not trading?**
```bash
# Enable debug logging in strategy
print(f"DEBUG: {should_open=}, {direction=}, {reason=}")

# Check market data availability
python3 -c "from pacifica_bot import PacificaAPI; api = PacificaAPI(); print(api.get_market_data('SOL'))"
```

---

## Best Practices

1. **One strategy, one file** - Don't combine multiple strategies
2. **Version control** - Git tag successful versions
3. **Test first** - Dry run before live trading
4. **Small positions** - Start with $10-20 for new strategies
5. **Monitor 24h** - Watch performance before scaling
6. **Document everything** - Update README.md immediately
7. **Keep old strategies** - Easy rollback if needed
8. **Separate concerns** - Strategy logic vs risk management vs execution
