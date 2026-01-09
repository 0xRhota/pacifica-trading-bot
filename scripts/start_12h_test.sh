#!/bin/bash
# Start 12-hour paper trade test with data validation monitoring
#
# This script:
# 1. Starts the paper trade (12 hours, 10-minute cycles)
# 2. Starts the monitor (checks every 30 minutes)
# 3. Logs both to separate files
#
# Usage: ./scripts/start_12h_test.sh

set -e

echo "=============================================="
echo "12-HOUR PAPER TRADE TEST"
echo "=============================================="
echo "Started: $(date)"
echo ""

# Create logs directory
mkdir -p logs

# Clear old logs
> logs/unified_paper_trade.log
> logs/data_validation_monitor.log

echo "Starting paper trade (12 hours)..."
echo "  Log: logs/unified_paper_trade.log"
nohup python3.11 scripts/unified_paper_trade.py --hours 12 --cycle 10 > logs/unified_paper_trade.log 2>&1 &
PAPER_PID=$!
echo "  PID: $PAPER_PID"

# Wait a few seconds for paper trade to initialize
sleep 5

echo ""
echo "Starting data validation monitor (30-minute checks)..."
echo "  Log: logs/data_validation_monitor.log"
nohup python3.11 scripts/monitor_paper_trade_v2.py > /dev/null 2>&1 &
MONITOR_PID=$!
echo "  PID: $MONITOR_PID"

echo ""
echo "=============================================="
echo "BOTH PROCESSES STARTED"
echo "=============================================="
echo ""
echo "Paper Trade PID: $PAPER_PID"
echo "Monitor PID:     $MONITOR_PID"
echo ""
echo "View logs:"
echo "  tail -f logs/unified_paper_trade.log"
echo "  tail -f logs/data_validation_monitor.log"
echo ""
echo "Stop all:"
echo "  kill $PAPER_PID $MONITOR_PID"
echo ""
echo "Or use:"
echo "  pkill -f unified_paper_trade"
echo "  pkill -f monitor_paper_trade"
echo ""
echo "Test will complete at: $(date -d '+12 hours' 2>/dev/null || date -v+12H)"
