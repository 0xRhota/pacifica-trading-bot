# RBI Agent - Research-Based Inference Strategy Discovery

**Status**: MVP Implemented  
**Date**: 2025-11-01  
**Purpose**: Automated strategy discovery and backtesting system

---

## Overview

The RBI (Research-Based Inference) Agent is inspired by Moon Dev's RBI agent. It automatically discovers, backtests, and validates trading strategies using historical data from Cambrian API (multi-venue aggregated) with automatic fallback to Pacifica API.

**Key Concept**: Instead of manually tweaking prompts, the bot discovers what works through automated backtesting.

---

## Architecture

```
Strategy Description (Natural Language)
  ↓
LLM Generates Backtest Code
  ↓
StrategyBacktester Executes on Historical Data
  ↓
Performance Metrics Calculated
  ↓
Pass/Fail Decision Based on Thresholds
```

---

## Files

### Core Implementation
- `rbi_agent/rbi_agent.py` - Main RBI agent class
  - `RBIAgent` - Strategy discovery and testing
  - `StrategyBacktester` - Backtesting engine

### Dependencies (Existing, Not Modified)
- `llm_agent/data/pacifica_fetcher.py` - Historical data fetching (fallback)
- `llm_agent/data/indicator_calculator.py` - Technical indicators
- `llm_agent/llm/model_client.py` - LLM for code generation
- `rbi_agent/cambrian_fetcher.py` - Cambrian API data fetcher ⭐ NEW

---

## Usage

### Basic Usage

```python
from rbi_agent.rbi_agent import RBIAgent

# Initialize agent
agent = RBIAgent()

# Test a strategy
result = agent.test_strategy(
    strategy_description="Buy when RSI < 30 and volume increases 30%",
    symbols=["SOL", "ETH", "BTC"],
    days_back=30
)

if result['passed']:
    print(f"✅ Strategy passed: {result['return_pct']:.2f}% return")
else:
    print(f"❌ Strategy failed: {result['return_pct']:.2f}% return")
```

### Command Line Usage

```bash
python -m rbi_agent.rbi_agent \
    --strategy "Buy when RSI < 35 and funding rate < 0" \
    --symbols SOL ETH BTC \
    --days 30 \
    --min-return 1.0
```

---

## How It Works

### 1. Strategy Description → Code Generation

**Input**: Natural language strategy description
```
"Buy when RSI < 30 and volume increases 30%"
```

**Process**: LLM (DeepSeek) generates Python function:
```python
def get_signal(df, i):
    if df.iloc[i]['rsi'] < 30:
        # Check volume increase
        if i > 0:
            volume_increase = (df.iloc[i]['volume'] - df.iloc[i-1]['volume']) / df.iloc[i-1]['volume']
            if volume_increase > 0.3:
                return "BUY"
    return None
```

### 2. Backtesting Execution

**Data**: Historical OHLCV candles from Pacifica API
- Fetches last N days of data
- Calculates indicators (RSI, MACD, SMA, BBands)
- Executes strategy code on each candle

**Execution**: Simulates trades
- Opens position on BUY signal
- Closes position on SELL/CLOSE signal
- Tracks P&L for each trade
- Calculates performance metrics

### 3. Performance Metrics

**Calculated Metrics**:
- `return_pct`: Total return percentage
- `win_rate`: Percentage of winning trades
- `sharpe_ratio`: Risk-adjusted return metric
- `max_drawdown`: Maximum peak-to-trough decline
- `total_trades`: Number of trades executed

### 4. Pass/Fail Criteria

**Default Thresholds**:
- Return > 1.0%
- Win Rate > 40%
- Sharpe Ratio > 0.5
- Minimum 5 trades

---

## Integration with Main Bot

### Current Status: Standalone Tool

The RBI agent is currently a **standalone tool** that does NOT modify the live bot.

### Future Integration Options

**Option 1: Manual Review**
- Run RBI agent manually
- Review results
- Manually add successful strategies to prompt

**Option 2: Auto-Discovery Mode**
- RBI agent runs weekly
- Tests 10-20 new strategies
- Saves passing strategies to file
- Bot references proven strategies in prompt

**Option 3: Auto-Integration**
- RBI agent automatically adds successful strategies
- Bot uses both: fixed prompt + discovered strategies
- Fully automated evolution

---

## Example Output

```
================================================================================
RBI BACKTEST RESULTS
================================================================================
Strategy: Buy when RSI < 30 and volume increases 30%
Status: ✅ PASSED
Return: 3.2%
Win Rate: 45.0%
Sharpe Ratio: 0.8
Max Drawdown: 8.5%
Total Trades: 12

Results by Symbol:
  SOL: 4.1% return, 50.0% win rate, 4 trades
  ETH: 2.8% return, 40.0% win rate, 5 trades
  BTC: 2.7% return, 45.0% win rate, 3 trades
================================================================================
```

---

## Strategy Code Generation

The LLM generates a function `get_signal(df, i)` that:
- Takes DataFrame `df` with OHLCV + indicators
- Takes index `i` for current candle
- Returns: `"BUY"`, `"SELL"`, `"CLOSE"`, or `None`

**Available Indicators**:
- `rsi` - RSI(14)
- `sma_20`, `sma_50` - Moving averages
- `macd`, `macd_signal`, `macd_hist` - MACD
- `bbands_upper`, `bbands_middle`, `bbands_lower` - Bollinger Bands
- `open`, `high`, `low`, `close`, `volume` - OHLCV

---

## Testing Multiple Strategies

### Batch Testing

```python
strategies = [
    "Buy when RSI < 30",
    "Sell when RSI > 70 and funding rate > 0.1%",
    "Buy when price crosses SMA(20) from below with high volume"
]

results = []
for strategy in strategies:
    result = agent.test_strategy(strategy)
    results.append(result)

# Sort by return
results.sort(key=lambda x: x['return_pct'], reverse=True)

# Get top 3
top_strategies = results[:3]
```

---

## Limitations & Considerations

### Current Limitations
1. **Historical Data Only** - Tests on past data, not future performance
2. **Simple Execution** - No slippage, fees, or order book simulation
3. **Single Symbol Testing** - Tests each symbol independently
4. **No Optimization** - Tests strategy as-is, doesn't optimize parameters

### Future Enhancements
- Multi-symbol portfolio testing
- Parameter optimization (grid search)
- Walk-forward analysis
- Paper trading validation
- Integration with main bot

---

## Safety & Isolation

**Important**: The RBI agent does NOT modify any live bot code.

- ✅ Uses existing data fetchers (read-only)
- ✅ Generates code in memory (not saved)
- ✅ No live trading
- ✅ No prompt modifications
- ✅ Completely isolated from `llm_agent/` directory

---

## Related Documentation

- `research/moon-dev/NEW_INSIGHTS_ANALYSIS.md` - Moon Dev RBI agent analysis
- `AGENTS.md` - Agent collaboration guide
- `docs/STRATEGY_MANAGEMENT.md` - Strategy management docs

---

## References

- Moon Dev RBI Agent: https://github.com/moondevonyt/moon-dev-ai-agents
- Backtesting.py Library: https://kernc.github.io/backtesting.py/
- Pacifica API Docs: https://docs.pacifica.fi/

---

**Last Updated**: 2025-11-01  
**Status**: MVP Complete - Ready for Testing

