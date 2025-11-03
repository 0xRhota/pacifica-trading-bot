# 🚀 Moon Dev RBI Agent - Ready to Run!

**Status**: ✅ Cambrian Data Prepared | ✅ Strategy Ideas Ready | ✅ Paths Updated

---

## ✅ What's Ready

### Cambrian CSV Files
- **SOL-USD-15m.csv**: 8,523 candles (90 days) ✅
- **ETH-USD-15m.csv**: 8,523 candles (90 days) ✅
- **BTC-USD-15m.csv**: Available (existing file)

**Location**: `moon-dev-reference/src/data/rbi/`

### Strategy Ideas
- **10 strategies** ready in `ideas.txt`
- Location: `moon-dev-reference/src/data/rbi_pp_multi/ideas.txt`

### Moon Dev RBI Agent
- **Code**: `moon-dev-reference/src/agents/rbi_agent_pp_multi.py`
- **Paths Updated**: ✅ Points to our CSV files
- **Target Return**: 50% (optimizes to hit this)
- **Save Threshold**: 1% (saves strategies > 1%)
- **Max Optimization**: 10 iterations per strategy

---

## 🚀 Quick Start

### Step 1: Install Dependencies
```bash
pip3 install backtesting pandas_ta termcolor
# Note: talib-binary may need manual installation if needed
```

### Step 2: Run Moon Dev RBI Agent
```bash
cd moon-dev-reference
python src/agents/rbi_agent_pp_multi.py
```

### Step 3: Check Results
```bash
# Strategies saved to:
moon-dev-reference/src/data/rbi_pp_multi/[DATE]/backtests_final/

# Stats CSV:
moon-dev-reference/src/data/rbi_pp_multi/backtest_stats.csv
```

---

## 📊 What Moon Dev RBI Agent Does

1. **Reads 10 strategies** from `ideas.txt`
2. **Generates backtest code** using LLM
3. **Tests on Cambrian data** (SOL, ETH CSV files)
4. **Optimizes strategies** up to 10 times to hit 50% target return
5. **Saves strategies** that pass 1% threshold
6. **Multi-data testing** (tests on multiple symbols automatically)

---

## 📁 Files Created

- `rbi_agent/cambrian_csv_adapter.py` - Cambrian → CSV converter ✅
- `rbi_agent/setup_moon_dev_rbi.py` - Setup script ✅
- `rbi_agent/run_moon_dev_rbi.py` - Runner script ✅
- `rbi_agent/quick_start_moon_dev.py` - Quick status check ✅
- `rbi_agent/MOON_DEV_READY.md` - This file ✅
- `moon-dev-reference/src/data/rbi/SOL-USD-15m.csv` - Cambrian SOL data ✅
- `moon-dev-reference/src/data/rbi/ETH-USD-15m.csv` - Cambrian ETH data ✅

---

## 🎯 Expected Results

Moon Dev RBI agent will:
- Test 10 strategies
- Optimize each up to 10 times
- Try to hit 50% target return
- Save strategies that pass 1% threshold
- Use Cambrian multi-venue aggregated data

**Result**: Optimized strategies ready to use in your trading bot!

---

## 💡 Next Steps After Running

1. **Review strategies** in `backtest_stats.csv`
2. **Check top performers** (sorted by return %)
3. **Add to bot prompt** or use for manual trading
4. **Run more discovery** with different strategies

---

**Status**: ✅ Ready to discover optimized strategies with Cambrian data!

**Run**: `cd moon-dev-reference && python src/agents/rbi_agent_pp_multi.py`

