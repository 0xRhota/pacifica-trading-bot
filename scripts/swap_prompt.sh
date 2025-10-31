#!/bin/bash
# Prompt Version Swapper
# Usage: ./scripts/swap_prompt.sh [version]
# Example: ./scripts/swap_prompt.sh v1  (revert to baseline)
#          ./scripts/swap_prompt.sh v2  (aggressive swing)

set -e

VERSION=$1
PROMPT_FILE="llm_agent/llm/prompt_formatter.py"
ARCHIVE_DIR="llm_agent/prompts_archive"

if [ -z "$VERSION" ]; then
    echo "Available prompt versions:"
    echo ""
    ls -1 $ARCHIVE_DIR/*.txt | xargs -n1 basename | sed 's/.txt//'
    echo ""
    echo "Usage: ./scripts/swap_prompt.sh [version]"
    echo "Example: ./scripts/swap_prompt.sh v1_baseline_conservative"
    exit 1
fi

PROMPT_ARCHIVE="$ARCHIVE_DIR/${VERSION}.txt"

if [ ! -f "$PROMPT_ARCHIVE" ]; then
    echo "Error: Prompt version '$VERSION' not found"
    echo "Available versions:"
    ls -1 $ARCHIVE_DIR/*.txt | xargs -n1 basename | sed 's/.txt//'
    exit 1
fi

echo "📝 Swapping to prompt version: $VERSION"
echo ""

# Read the prompt from archive
PROMPT_CONTENT=$(cat "$PROMPT_ARCHIVE")

# Use Python to replace the instructions section
python3 - <<EOF
import re

# Read current file
with open('$PROMPT_FILE', 'r') as f:
    content = f.read()

# Read new prompt
with open('$PROMPT_ARCHIVE', 'r') as f:
    new_prompt = f.read()

# Replace the instructions variable (between 'instructions = """' and '"""')
pattern = r'(        # Instructions\n        instructions = """).*?(""")'
replacement = r'\1' + new_prompt + r'\2'
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('$PROMPT_FILE', 'w') as f:
    f.write(new_content)

print(f"✅ Updated {PROMPT_FILE}")
EOF

echo ""
echo "🔄 Restart bot to apply changes:"
echo "   pkill -f llm_agent.bot_llm"
echo "   nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &"
echo ""
echo "📊 Monitor decisions:"
echo "   python3 scripts/view_decisions.py"
