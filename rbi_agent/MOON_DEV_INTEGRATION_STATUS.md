# Moon Dev RBI Agent Integration - Status

**Date**: 2025-11-01  
**Status**: ✅ Ready to Integrate

---

## What We Found

### Moon Dev's RBI Agent (`rbi_agent_pp_multi.py`)

**Key Features**:
- ✅ **Optimization Loop**: `optimize_strategy()` function
- ✅ **Target Return**: 50% (optimizes to hit this)
- ✅ **Max Iterations**: 10 optimization attempts
- ✅ **Uses `backtesting.py` library**: Professional backtesting framework
- ✅ **Parallel Processing**: Up to 18 threads simultaneously
- ✅ **Multi-Data Testing**: Tests on 25+ data sources automatically

**Configuration**:
```python
TARGET_RETURN = 50  # Target return in %
SAVE_IF_OVER_RETURN = 1.0  # Save if return > 1%
MAX_OPTIMIZATION_ITERATIONS = 10
```

**How Optimization Works**:
1. Generates initial backtest code
2. Runs backtest, gets return %
3. If return < target (50%), calls `optimize_strategy()`
4. LLM improves the strategy code
5. Re-runs backtest
6. Repeats up to 10 times until target met

---

## Integration Plan

### Step 1: Install Dependencies
```bash
pip install backtesting pandas-ta talib-binary
```

### Step 2: Create Data Adapter
- Convert Pacifica/Cambrian OHLCV → CSV format Moon Dev expects
- Format: `datetime,open,high,low,close,volume`
- Save to `src/data/rbi/SYMBOL-TIMEFRAME.csv`

### Step 3: Adapt Moon Dev's Code
- Point to our data sources
- Use our API keys (DeepSeek, etc.)
- Keep their optimization logic intact

### Step 4: Run RBI Agent
```bash
# Create ideas.txt with strategies
echo "Buy when RSI < 30" > src/data/rbi_pp_multi/ideas.txt

# Run Moon Dev's RBI agent
python src/agents/rbi_agent_pp_multi.py
```

---

## Files from Moon Dev

**Location**: `moon-dev-reference/`
- `src/agents/rbi_agent_pp_multi.py` - Main RBI agent (1700+ lines)
- `src/models/model_factory.py` - Model abstraction
- `requirements.txt` - Dependencies

**Key Functions**:
- `optimize_strategy()` - Iterative optimization loop
- `execute_backtest()` - Runs backtest.py code
- `save_backtest_if_threshold_met()` - Saves passing strategies

---

## Next Steps

1. **Install dependencies** (`backtesting.py`, `pandas-ta`, `talib`)
2. **Create data adapter** to convert our data → Moon Dev format
3. **Run Moon Dev's RBI agent** with our data sources
4. **Get optimized strategies** that hit 50% target return!

---

**Status**: ✅ Ready to integrate Moon Dev's actual RBI agent code!

