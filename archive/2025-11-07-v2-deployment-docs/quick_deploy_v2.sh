#!/bin/bash
# Quick V2 Deployment Script
# Usage: ./quick_deploy_v2.sh

echo "🚀 Deploying V2 Deep Reasoning Prompt"
echo "======================================"
echo ""

# Stop any running bot
echo "1. Stopping current bot..."
pkill -f "lighter_agent.bot_lighter"
sleep 3

# Backup current log
echo "2. Backing up V1 log..."
if [ -f logs/lighter_bot.log ]; then
    cp logs/lighter_bot.log logs/lighter_bot_V1_backup_$(date +%Y%m%d_%H%M%S).log
    echo "   ✅ V1 log backed up"
else
    echo "   ⚠️  No existing log to backup"
fi

# Start V2 (config already set to v2_deep_reasoning)
echo "3. Starting V2..."
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
sleep 5

# Verify bot started
PID=$(pgrep -f "lighter_agent.bot_lighter")
if [ -z "$PID" ]; then
    echo "   ❌ Bot failed to start!"
    echo "   Check logs: tail -100 logs/lighter_bot.log"
    exit 1
else
    echo "   ✅ Bot started (PID: $PID)"
fi

# Verify V2 is active
echo "4. Verifying V2 is active..."
sleep 10
VERSION=$(tail -50 logs/lighter_bot.log | grep "Active Prompt Version" | tail -1)
if [[ $VERSION == *"v2_deep_reasoning"* ]]; then
    echo "   ✅ V2 Deep Reasoning confirmed"
elif [[ $VERSION == *"v1_original"* ]]; then
    echo "   ⚠️  WARNING: V1 Original is active (not V2!)"
    echo "   Check llm_agent/config_prompts.py line 20"
    exit 1
else
    echo "   ❓ Version unclear - waiting for first log entry..."
fi

echo ""
echo "======================================"
echo "✅ V2 Deployment Complete"
echo "======================================"
echo ""
echo "📊 Monitor live decisions:"
echo "   ./monitor_v2.sh"
echo ""
echo "Or manually:"
echo "   tail -f logs/lighter_bot.log | grep -E 'Decision Cycle.*V2|LLM DECISIONS|Order placed|FILLED' --line-buffered --color=always"
echo ""
echo "First decision cycle in ~5 minutes"
echo ""
