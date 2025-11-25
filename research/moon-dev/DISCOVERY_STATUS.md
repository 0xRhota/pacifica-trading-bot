# Strategy Discovery - Quick Reference

**Status**: ✅ Automated Discovery Running  
**Start Time**: See `logs/rbi_discovery.log`  
**Duration**: 2 hours (running continuously)

---

## When You Return

### Check Status
```bash
# Health check
python3 rbi_agent/health_check.py

# View discovered strategies
python3 rbi_agent/show_discovered_strategies.py

# Check logs
tail -f logs/rbi_auto_discovery.log
```

### View Results
```bash
# Quick summary
python3 rbi_agent/show_discovered_strategies.py

# Full results (JSON)
cat rbi_agent/proven_strategies.json | jq .
```

---

## What's Running

**Process**: `auto_discover_strategies.py`
- **Duration**: 2 hours
- **Check Interval**: Every 30 minutes
- **Strategies Tested**: 19 strategies per run
- **Symbols**: SOL, ETH, BTC (Cambrian API)
- **Period**: 90 days historical data
- **Thresholds**: Return > 1%, Win Rate > 40%, Sharpe > 0.5

**Expected Output**:
- Proven strategies saved to `rbi_agent/proven_strategies.json`
- Logs saved to `logs/rbi_auto_discovery.log`
- Auto-runs every 30 minutes for 2 hours (~4 discovery runs total)

---

## Discovery Process

1. **Tests 19 strategies** on SOL, ETH, BTC (90 days)
2. **Filters by thresholds**:
   - Return > 1%
   - Win Rate > 40%
   - Sharpe Ratio > 0.5
   - Minimum 5 trades
3. **Saves proven strategies** to JSON file
4. **Repeats every 30 minutes** for 2 hours

---

## Files

- `rbi_agent/auto_discover_strategies.py` - Main discovery runner
- `rbi_agent/health_check.py` - Health check script
- `rbi_agent/show_discovered_strategies.py` - View results
- `rbi_agent/proven_strategies.json` - Discovered strategies (created)
- `logs/rbi_auto_discovery.log` - Discovery logs

---

## Monitoring

**Check if running**:
```bash
ps aux | grep auto_discover_strategies
```

**Watch logs**:
```bash
tail -f logs/rbi_auto_discovery.log
```

**Check health**:
```bash
python3 rbi_agent/health_check.py
```

---

## Results Format

Each proven strategy includes:
- `strategy_name`: Name of strategy
- `description`: Natural language description
- `code`: Generated Python backtest code
- `return_pct`: Total return percentage
- `win_rate`: Win rate (0-1)
- `sharpe_ratio`: Sharpe ratio
- `max_drawdown`: Maximum drawdown %
- `total_trades`: Number of trades
- `results_by_symbol`: Results broken down by symbol
- `discovered_at`: Timestamp when discovered

---

## Next Steps (When You Return)

1. **View discovered strategies**:
   ```bash
   python3 rbi_agent/show_discovered_strategies.py
   ```

2. **Review top performers**:
   - Check return %, win rate, Sharpe ratio
   - Review results by symbol

3. **Integrate into bot**:
   - Manually add top strategies to prompt
   - Or use for manual trading decisions

4. **Run more discovery**:
   ```bash
   python3 rbi_agent/auto_discover_strategies.py --hours 4 --check-interval 60
   ```

---

**Discovery Status**: ✅ Running  
**Check Back**: In ~2 hours for results  
**Log File**: `logs/rbi_auto_discovery.log`


