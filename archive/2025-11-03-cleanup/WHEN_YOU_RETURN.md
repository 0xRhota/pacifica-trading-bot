# ⭐ When You Return - Quick Start Guide

**Discovery Status**: ✅ Running (will complete in ~2 hours)  
**Created**: 2025-11-01

---

## 🚀 Quick Commands (Copy & Paste)

### Check Status
```bash
python3 rbi_agent/health_check.py
```

### View Discovered Strategies
```bash
python3 rbi_agent/show_discovered_strategies.py
```

### View Logs
```bash
tail -50 logs/rbi_discovery.log
```

### View Proven Strategies (JSON)
```bash
cat rbi_agent/proven_strategies.json | jq .
```

---

## 📊 What's Happening

**Process**: Automated Strategy Discovery  
**Status**: ✅ Running (PID: 96136)  
**Duration**: 2 hours total  
**Runs**: Every 30 minutes (~4 discovery runs)

**Each Run**:
- Tests 19 strategies
- On SOL, ETH, BTC (90 days historical data)
- Uses Cambrian API (multi-venue aggregated)
- Saves proven strategies that pass thresholds

**Thresholds**:
- Return > 1%
- Win Rate > 40%
- Sharpe Ratio > 0.5
- Minimum 5 trades

---

## 📁 Results Location

**Proven Strategies**: `rbi_agent/proven_strategies.json`
- Created automatically when strategies are found
- Contains all strategies that passed thresholds
- Sorted by return % (highest first)

**Logs**: `logs/rbi_discovery.log`
- Complete discovery process logs
- Shows which strategies passed/failed
- Timestamps for each run

---

## 🔍 Expected Results

When you return, you should have:
- ✅ Proven strategies file (if any strategies passed)
- ✅ Complete discovery logs
- ✅ Performance metrics for each strategy
- ✅ Results broken down by symbol

**If no strategies found**:
- Thresholds may be too strict
- Check logs for details
- Can lower thresholds and re-run

---

## 📚 Documentation

- `rbi_agent/WELCOME_BACK.md` - Welcome back guide
- `rbi_agent/DISCOVERY_STATUS.md` - Discovery status details
- `rbi_agent/AUTO_DISCOVERY_SETUP.md` - Setup documentation
- `USER_REFERENCE.md` - Quick reference (updated with discovery commands)

---

## ⚠️ Troubleshooting

**If discovery stopped**:
```bash
# Check logs
tail -100 logs/rbi_discovery.log

# Restart
nohup python3 rbi_agent/auto_discover_strategies.py --hours 2 --check-interval 30 > logs/rbi_discovery.log 2>&1 &
```

**If no strategies found**:
```bash
# Try with lower thresholds
python3 rbi_agent/auto_discover_strategies.py --once --min-return 0.5 --min-win-rate 0.35 --min-sharpe 0.3
```

---

## ✅ Everything is Set Up

- ✅ Discovery process running
- ✅ Health check script ready
- ✅ Results viewer ready
- ✅ Documentation complete
- ✅ Logs being written

**Just run**: `python3 rbi_agent/show_discovered_strategies.py` when you return!

