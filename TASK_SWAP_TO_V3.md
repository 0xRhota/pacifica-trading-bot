# Prompt Swap Request: v3_longer_holds

**Task**: Swap the LLM bot prompt to v3_longer_holds to fix premature position closing issue

## What to Do

1. **Swap the prompt**:
   ```bash
   ./scripts/swap_prompt.sh v3_longer_holds
   ```

2. **Restart the bot**:
   ```bash
   pkill -f "llm_agent.bot_llm"
   sleep 2
   nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
   echo "Bot restarted with PID: $!"
   ```

3. **Verify it's running**:
   ```bash
   ps aux | grep llm_agent.bot_llm | grep -v grep
   tail -20 logs/llm_bot.log
   ```

## What Changed

**Problem**: Bot was closing positions too quickly (8 minutes) - fees were eating into small profits

**Fix**: Updated prompt to tell LLM:
- ✅ Close IMMEDIATELY if profit target hit (+1.5% to +3%)
- ✅ Close IMMEDIATELY if stop loss hit (-1% to -1.5%)
- ❌ Don't close just because position is "flat" after 5 minutes
- ❌ Don't close prematurely - let swing trades develop

**Key Point**: If profit target is hit in 5 minutes, take it! But don't close early just because position hasn't moved much yet.

## Expected Behavior

**Before**: Bot closing positions after 8 minutes, breaking even or small losses due to fees

**After**: Bot should:
- Hold positions longer when they're developing
- Close immediately when profit targets hit
- Close immediately when stop losses hit
- Not close prematurely just because position is flat

## File Location

Prompt file: `llm_agent/prompts_archive/v3_longer_holds.txt`

## Verification

After swapping, check that the prompt was applied:
```bash
grep -A 5 "POSITION MANAGEMENT" llm_agent/llm/prompt_formatter.py
```

Should see the new position management section with fee considerations and exit rules.

---

**That's it** - just swap and restart. Monitor logs to see if bot holds positions longer now.

