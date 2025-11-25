# Bot Status - Nov 9, 2025 10:29 AM

## ✅ Both Bots Running

### Pacifica Bot
- **Status**: ✅ Running (PID: 525)
- **Strategy**: Swing trading (v1_original)
- **Check Interval**: 5 minutes
- **Max Hold Time**: 48 hours
- **Position Size**: $250 ($5 margin @ 50x leverage)
- **Next Cycle**: Every 5 minutes
- **Log**: `logs/pacifica_bot.log`

**Stop**: `pkill -f "pacifica_agent.bot_pacifica"`
**Restart**: `nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 >> logs/pacifica_bot.log 2>&1 &`

### Lighter Bot
- **Status**: ✅ Running (PID: 29819)
- **Strategy**: Momentum (v4) with **Confidence-Based Holds**
- **Check Interval**: 5 minutes
- **Position Hold Logic**:
  - **High confidence (≥0.7)**: Minimum 2 hour hold (let winners run)
  - **Low confidence (<0.7)**: Can close early
- **Max Hold Time**: 4 hours (auto-close aging positions)
- **Position Size**: $2 per trade
- **Next Cycle**: Every 5 minutes
- **Log**: `logs/lighter_bot.log`

**Stop**: `pkill -f "lighter_agent.bot_lighter"`
**Restart**: `nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 >> logs/lighter_bot.log 2>&1 &`

## 🔍 Automated Monitoring

**Monitoring Script**: `scripts/monitor_bots.sh`
- Checks both bots every 10 minutes
- Auto-restarts if either bot stops
- Logs to: `logs/bot_monitor.log`
- Monitor loop PID: 22432

**Stop Monitoring**: `pkill -f "monitor_bots"`

## 📊 Quick Commands

```bash
# Check if bots are running
pgrep -af "bot_pacifica\|bot_lighter"

# View recent Pacifica activity
tail -50 logs/pacifica_bot.log | grep "DECISION CYCLE\|NEXT CYCLE\|FILLED"

# View recent Lighter activity
tail -50 logs/lighter_bot.log | grep "DECISION CYCLE\|NEXT CYCLE\|FILLED"

# Check monitoring log
tail -f logs/bot_monitor.log

# Manual monitor check
./scripts/monitor_bots.sh
```

## 🎯 Current Configuration

**Pacifica**:
- Swing trades targeting 3-5% profits
- Requires 4h ADX > 30 for entries
- Checks every 5 minutes but holds up to 48 hours
- Min confidence: 0.7 (high conviction only)

**Lighter**:
- Momentum strategy with AI decisions
- 101+ markets dynamically loaded
- Zero fees (Lighter DEX advantage)
- Position aging: auto-close after 4 hours

---
**Last Updated**: Nov 9, 2025 10:29 AM
**Both bots confirmed running with automated monitoring active**
