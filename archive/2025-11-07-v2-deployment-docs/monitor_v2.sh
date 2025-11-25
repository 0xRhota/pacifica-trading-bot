#!/bin/bash
# V2 Bot Monitoring Script
# Usage: ./monitor_v2.sh

echo "🤖 Lighter Bot V2 Monitor"
echo "=========================="
echo ""

# Check if bot is running
PID=$(pgrep -f "lighter_agent.bot_lighter")
if [ -z "$PID" ]; then
    echo "❌ Bot is NOT running"
    echo ""
    echo "Start bot with:"
    echo "  nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &"
    exit 1
else
    echo "✅ Bot is running (PID: $PID)"
fi

# Check version
echo ""
echo "📋 Checking Active Version..."
VERSION=$(tail -100 logs/lighter_bot.log | grep "Active Prompt Version" | tail -1)
if [[ $VERSION == *"v2_deep_reasoning"* ]]; then
    echo "✅ V2 Deep Reasoning is active"
elif [[ $VERSION == *"v1_original"* ]]; then
    echo "⚠️  V1 Original is active (not V2)"
else
    echo "❓ Version unclear - check logs"
fi

echo ""
echo "📊 Recent Activity (last 5 minutes):"
echo "----------------------------------------"
tail -200 logs/lighter_bot.log | grep -E "Decision Cycle.*V2|LLM DECISIONS|Executing decision|Order placed|FILLED|CANCELED" | tail -10

echo ""
echo "🔍 Live Monitoring (Ctrl+C to exit):"
echo "----------------------------------------"
echo ""

# Live tail with filtering and color
tail -f logs/lighter_bot.log | grep -E "Decision Cycle|V2 \(Deep Reasoning\)|LLM DECISIONS|Executing decision|Order placed|FILLED|CANCELED|REJECTED" --line-buffered --color=always
