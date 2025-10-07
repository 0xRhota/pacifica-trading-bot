#!/bin/bash
echo "==================================================="
echo "PACIFICA DRY RUN BOT STATUS"
echo "==================================================="
echo ""
echo "Last 30 log lines:"
echo "---------------------------------------------------"
tail -30 <(python3 -c "
import sys
sys.path.insert(0, '.')
lines = []
try:
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    if 'dry_run_bot.py' in result.stdout:
        print('✅ Bot is RUNNING')
    else:
        print('❌ Bot is NOT running')
except:
    pass
" 2>/dev/null)

if [ -f dry_run.log ]; then
    tail -30 dry_run.log
else
    echo "No log file found yet"
fi

echo ""
echo "==================================================="
