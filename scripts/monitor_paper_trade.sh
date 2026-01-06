#!/bin/bash
# Monitor paper trade - check every 5 minutes for issues

LOG="/Users/admin/Documents/Projects/pacifica-trading-bot/logs/unified_paper_trade.log"
MONITOR_LOG="/Users/admin/Documents/Projects/pacifica-trading-bot/logs/monitor.log"

echo "$(date '+%H:%M:%S') | Monitor started" > $MONITOR_LOG

while true; do
    sleep 300  # 5 minutes
    
    # Check if process is still running
    if ! pgrep -f "unified_paper_trade.py" > /dev/null; then
        echo "$(date '+%H:%M:%S') | ⚠️ Paper trade process NOT RUNNING!" >> $MONITOR_LOG
        break
    fi
    
    # Get last 20 lines and check for issues
    LAST_LINES=$(tail -20 "$LOG")
    
    # Check for errors
    if echo "$LAST_LINES" | grep -qi "error\|exception\|failed\|critical"; then
        echo "$(date '+%H:%M:%S') | ❌ ERROR DETECTED in log!" >> $MONITOR_LOG
        echo "$LAST_LINES" | grep -i "error\|exception\|failed" >> $MONITOR_LOG
    fi
    
    # Check for health issues
    if echo "$LAST_LINES" | grep -q "❌.*No data"; then
        echo "$(date '+%H:%M:%S') | ❌ HEALTH CHECK FAILED - missing exchange data!" >> $MONITOR_LOG
    fi
    
    # Get current stats
    CYCLE=$(grep "CYCLE" "$LOG" | tail -1)
    POSITIONS=$(grep -E "OPEN (LONG|SHORT)" "$LOG" | wc -l | tr -d ' ')
    BALANCE_LINE=$(grep "Balance:" "$LOG" | tail -3)
    
    echo "$(date '+%H:%M:%S') | ✅ Running | $CYCLE | Positions opened: $POSITIONS" >> $MONITOR_LOG
    
    # Check if test completed
    if grep -q "FINAL REPORT" "$LOG"; then
        echo "$(date '+%H:%M:%S') | 🏁 Paper trade COMPLETED" >> $MONITOR_LOG
        break
    fi
done

echo "$(date '+%H:%M:%S') | Monitor stopped" >> $MONITOR_LOG
