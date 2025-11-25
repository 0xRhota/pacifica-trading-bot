#!/bin/bash
# Bot monitoring script - checks both Pacifica and Lighter bots every 5 minutes

LOG_FILE="logs/bot_monitor.log"
PACIFICA_LOG="logs/pacifica_bot.log"
LIGHTER_LOG="logs/lighter_bot.log"

echo "=== Bot Monitor Check: $(date) ===" | tee -a "$LOG_FILE"

# Check Pacifica bot
PACIFICA_PID=$(pgrep -f "pacifica_agent.bot_pacifica" | head -1)
if [ -n "$PACIFICA_PID" ]; then
    LAST_ACTIVITY=$(tail -1 "$PACIFICA_LOG")
    echo "✅ Pacifica bot running (PID: $PACIFICA_PID)" | tee -a "$LOG_FILE"
    echo "   Last activity: $LAST_ACTIVITY" | tee -a "$LOG_FILE"
else
    echo "❌ Pacifica bot NOT running - attempting restart..." | tee -a "$LOG_FILE"
    nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 >> "$PACIFICA_LOG" 2>&1 &
    sleep 2
    NEW_PID=$(pgrep -f "pacifica_agent.bot_pacifica" | head -1)
    if [ -n "$NEW_PID" ]; then
        echo "   ✅ Restarted (PID: $NEW_PID)" | tee -a "$LOG_FILE"
    else
        echo "   ❌ Failed to restart" | tee -a "$LOG_FILE"
    fi
fi

# Check Lighter bot
LIGHTER_PID=$(pgrep -f "lighter_agent.bot_lighter" | head -1)
if [ -n "$LIGHTER_PID" ]; then
    LAST_ACTIVITY=$(tail -1 "$LIGHTER_LOG")
    echo "✅ Lighter bot running (PID: $LIGHTER_PID)" | tee -a "$LOG_FILE"
    echo "   Last activity: $LAST_ACTIVITY" | tee -a "$LOG_FILE"
else
    echo "❌ Lighter bot NOT running - attempting restart..." | tee -a "$LOG_FILE"
    nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 >> "$LIGHTER_LOG" 2>&1 &
    sleep 2
    NEW_PID=$(pgrep -f "lighter_agent.bot_lighter" | head -1)
    if [ -n "$NEW_PID" ]; then
        echo "   ✅ Restarted (PID: $NEW_PID)" | tee -a "$LOG_FILE"
    else
        echo "   ❌ Failed to restart" | tee -a "$LOG_FILE"
    fi
fi

echo "" | tee -a "$LOG_FILE"
