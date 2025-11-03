## RBI Agent - Strategy Discovery

### View Discovered Strategies
```bash
python3 rbi_agent/show_discovered_strategies.py
```

### Check Discovery Health
```bash
python3 rbi_agent/health_check.py
```

### Start Discovery (2 hours)
```bash
nohup python3 rbi_agent/auto_discover_strategies.py --hours 2 --check-interval 30 > logs/rbi_discovery.log 2>&1 &
```

### Monitor Discovery Logs
```bash
tail -f logs/rbi_auto_discovery.log
```

### View Proven Strategies (JSON)
```bash
cat rbi_agent/proven_strategies.json | jq .
```

---

## Bot Management

```bash
# List available prompt versions
./scripts/swap_prompt.sh

# Swap to conservative (baseline)
./scripts/swap_prompt.sh v1_baseline_conservative

# Swap to aggressive swing trading
./scripts/swap_prompt.sh v2_aggressive_swing

# Restart bot after swapping
pkill -f "llm_agent.bot_llm"
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

**See `PROMPT_EXPERIMENTS.md` for full guide on creating/testing new prompts**

---

## 📊 View Bot Decisions

```bash
# Quick summary
python3 scripts/view_decisions.py

# Full breakdown (with reasoning, Deep42 queries, token analysis)
python3 scripts/view_decision_details.py
```

## 🤖 Bot Commands

```bash
# Check if running
ps aux | grep "[b]ot_llm"

# Stop bot
pkill -f "llm_agent.bot_llm"

# Start bot (LIVE) and validate
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
python3 scripts/validate_bot_startup.py

# View live log
tail -f logs/llm_bot.log
```

## 💼 Check Positions

```bash
curl -s "https://api.pacifica.fi/api/v1/positions?account=8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc" | python3 -m json.tool
```

## 🔍 Find Errors

```bash
grep -i "error\|failed" logs/llm_bot.log | tail -20
```

---

**That's it. Everything you need.**
