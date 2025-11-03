# Moon Dev RBI Agent - Setup Complete ✅

**Date**: 2025-11-01  
**Status**: ✅ Ready to Run

---

## What's Set Up

### ✅ Cambrian Data CSV Files
- **SOL-USD-15m.csv**: 8,523 candles (90 days) ✅
- **ETH-USD-15m.csv**: 8,523 candles (90 days) ✅
- **BTC-USD-15m.csv**: ❌ (No Cambrian data, can use existing file)

**Location**: `moon-dev-reference/src/data/rbi/`

### ✅ Strategy Ideas Created
- **10 strategies** added to `ideas.txt`
- Location: `moon-dev-reference/src/data/rbi_pp_multi/ideas.txt`

### ✅ Moon Dev RBI Agent
- **Location**: `moon-dev-reference/src/agents/rbi_agent_pp_multi.py`
- **Target Return**: 50% (optimizes to hit this)
- **Save Threshold**: 1% (saves strategies > 1%)
- **Max Optimization**: 10 iterations per strategy

---

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
python3 rbi_agent/setup_moon_dev_rbi.py
```

This will:
1. ✅ Check dependencies
2. ✅ Prepare Cambrian CSV files
3. ✅ Update Moon Dev data paths
4. ✅ Create strategy ideas
5. ✅ Run Moon Dev RBI agent

### Option 2: Manual Setup

**1. Install Dependencies**:
```bash
pip install backtesting pandas-ta talib-binary termcolor
```

**2. Prepare Cambrian Data**:
```bash
python3 rbi_agent/cambrian_csv_adapter.py
```

**3. Run Moon Dev RBI Agent**:
```bash
cd moon-dev-reference
python src/agents/rbi_agent_pp_multi.py
```

---

## What Moon Dev RBI Agent Does

1. **Reads strategy ideas** from `ideas.txt`
2. **Generates backtest code** using LLM
3. **Tests on Cambrian data** (SOL, ETH CSV files)
4. **Optimizes strategies** up to 10 times to hit 50% target return
5. **Saves strategies** that pass 1% threshold
6. **Multi-data testing** (tests on multiple symbols automatically)

---

## Expected Results

**Strategies saved to**:
- `moon-dev-reference/src/data/rbi_pp_multi/[DATE]/backtests_final/`
- `moon-dev-reference/src/data/rbi_pp_multi/backtest_stats.csv`

**Each strategy includes**:
- Python backtest code
- Performance metrics (return %, win rate, Sharpe ratio)
- Results across multiple symbols

---

## Files Created

- `rbi_agent/cambrian_csv_adapter.py` - Cambrian → CSV converter
- `rbi_agent/setup_moon_dev_rbi.py` - Setup and runner script
- `rbi_agent/run_moon_dev_rbi.py` - Simple runner
- `moon-dev-reference/src/data/rbi/SOL-USD-15m.csv` - Cambrian SOL data
- `moon-dev-reference/src/data/rbi/ETH-USD-15m.csv` - Cambrian ETH data

---

## Next Steps

1. **Run setup script**: `python3 rbi_agent/setup_moon_dev_rbi.py`
2. **Wait for results**: Moon Dev RBI agent will optimize strategies
3. **Review strategies**: Check `backtest_stats.csv` for proven strategies
4. **Use in bot**: Add top strategies to your trading bot prompt

---

**Status**: ✅ Ready to discover optimized strategies with Cambrian data!

