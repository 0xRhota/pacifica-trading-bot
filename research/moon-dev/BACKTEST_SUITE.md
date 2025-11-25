# RBI Backtest Suite - Documentation

**Status**: ✅ Implemented  
**Purpose**: Automated backtesting of multiple trading strategies on historical Pacifica data

---

## Overview

The backtest suite tests 19 different trading strategies across 4 symbols (SOL, ETH, BTC, PUMP) over the last 90 days to find the best performing strategies.

---

## Strategy Library

The suite tests strategies in these categories:

### Momentum Strategies
- RSI Oversold Long
- RSI Oversold + Volume
- MACD Bullish Cross
- RSI + MACD Long
- Multi-Indicator Long
- Volume Spike Long

### Mean Reversion Strategies
- RSI Overbought Short
- RSI Overbought + Volume
- BB Lower Band Bounce
- BB Upper Band Rejection

### Trend Following Strategies
- SMA Golden Cross
- SMA Death Cross
- Price Above SMA20
- Conservative RSI Long/Short

### Combined Strategies
- RSI + MACD (Long/Short)
- Multi-Indicator (Long/Short)
- Volume Spike (Long/Short)

---

## Usage

### Run Full Suite
```bash
python3 rbi_agent/backtest_suite.py --days 90 --symbols SOL ETH BTC PUMP
```

### Custom Thresholds
```bash
python3 rbi_agent/backtest_suite.py \
    --days 90 \
    --symbols SOL ETH BTC PUMP \
    --min-return 1.0 \
    --min-win-rate 0.40 \
    --min-sharpe 0.5
```

### Background Execution
```bash
nohup python3 rbi_agent/backtest_suite.py --days 90 > logs/rbi_backtest.log 2>&1 &
```

---

## Output

### Console Output
- Real-time progress for each strategy
- Pass/fail status
- Performance metrics (return %, win rate, Sharpe ratio, trades)

### Results File
- `rbi_agent/backtest_results.json` - Complete results with all strategies
- Includes:
  - All strategy results
  - Top 10 strategies (sorted by return)
  - Summary statistics
  - Results by symbol

### Example Output
```
TOP 10 STRATEGIES (by Return)
================================================================================

1. Strategy Name
   Category: momentum
   Description: Buy when RSI < 30
   ✅ Return: 3.2%
   Win Rate: 45.0%
   Sharpe Ratio: 0.8
   Max Drawdown: 8.5%
   Total Trades: 12
   Results by Symbol:
     SOL: 4.1% return, 50.0% win rate, 4 trades
     ETH: 2.8% return, 40.0% win rate, 5 trades
     ...
```

---

## Default Thresholds

**Pass Criteria**:
- Return > 0.5%
- Win Rate > 35%
- Sharpe Ratio > 0.3
- Minimum 5 trades

**Adjustable via command line arguments**

---

## Performance

**Expected Runtime**: ~20-30 minutes for full suite
- 19 strategies × 4 symbols = 76 backtests
- Each backtest: LLM code generation + data fetch + execution
- Progress saved incrementally

---

## Files

- `rbi_agent/backtest_suite.py` - Main backtest suite script
- `rbi_agent/backtest_results.json` - Results output (created after run)
- `logs/rbi_backtest.log` - Execution log (if run in background)

---

## Integration

**Current**: Standalone tool for strategy discovery

**Future**: 
- Auto-run weekly to discover new strategies
- Save passing strategies to `proven_strategies.json`
- Integrate top strategies into main bot prompt

---

**See**: `rbi_agent/README.md` for full RBI agent documentation


