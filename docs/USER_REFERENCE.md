# Trading Bots - Quick Reference

## 🤖 Active Bots

### Lighter Bot (zkSync)
- **Location**: `lighter_agent/bot_lighter.py`
- **Markets**: 101+ (BTC, SOL, DOGE, 1000PEPE, WIF, WLD, etc.)
- **Fees**: Zero
- **Account**: 341823 (API Key Index: 2)

### Pacifica Bot (Pacifica DEX)
- **Location**: `pacifica_agent/bot_pacifica.py`
- **Markets**: BTC, SOL, ETH, DOGE, etc.
- **Fees**: Check with exchange
- **Account**: `8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc`

**Both bots**:
- $5 per trade, max 15 positions
- 5-minute check interval (300 seconds)
- DeepSeek Chat LLM
- **Shared strategy**: Both use `llm_agent/llm/` (V2 Deep Reasoning)

---

## 📋 Common Commands

### View Logs
```bash
# Lighter bot
tail -f logs/lighter_bot.log          # Live
tail -100 logs/lighter_bot.log         # Last 100 lines

# Pacifica bot
tail -f logs/pacifica_bot.log          # Live
tail -100 logs/pacifica_bot.log        # Last 100 lines

# Find decisions (both bots)
tail -200 logs/lighter_bot.log | grep -A 5 "Decision Cycle"
tail -200 logs/pacifica_bot.log | grep -A 5 "Decision Cycle"

# Find trades (both bots)
tail -200 logs/lighter_bot.log | grep -E "FILLED|SUBMITTED"
tail -200 logs/pacifica_bot.log | grep -E "FILLED|SUBMITTED"

# Find errors (both bots)
tail -200 logs/lighter_bot.log | grep -i "error\|failed"
tail -200 logs/pacifica_bot.log | grep -i "error\|failed"
```

### Bot Control

#### Lighter Bot
```bash
# Check status
pgrep -f "lighter_agent.bot_lighter"

# Stop
pkill -f "lighter_agent.bot_lighter"

# Start (live)
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# Start (dry-run)
nohup python3 -u -m lighter_agent.bot_lighter --dry-run --interval 300 > logs/lighter_bot.log 2>&1 &
```

#### Pacifica Bot
```bash
# Check status
pgrep -f "pacifica_agent.bot_pacifica"

# Stop
pkill -f "pacifica_agent.bot_pacifica"

# Start (live)
nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 > logs/pacifica_bot.log 2>&1 &

# Start (dry-run)
nohup python3 -u -m pacifica_agent.bot_pacifica --dry-run --interval 300 > logs/pacifica_bot.log 2>&1 &
```

---

## 🔄 Strategy Switching

When changing strategies (new prompt, major config change, integrations), perform a **clean break**:

```bash
# 1. Stop bot
pkill -f "lighter_agent.bot_lighter"

# 2. Clean strategy switch (archives old tracker, creates fresh one)
python3 scripts/general/switch_strategy.py \
  --dex lighter \
  --strategy "strategy-name" \
  --reason "Brief reason"

# 3. Start bot with clean slate
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# 4. Verify clean start
tail -200 logs/lighter_bot.log | grep -E "(STALE|ghost|failed to close)" || echo "✅ Clean start!"
```

**Why this matters**:
- Prevents ghost positions (tracker out of sync with exchange)
- Clear performance boundaries for each strategy
- Easy rollback to previous strategy data
- Clear log markers for analysis

**See**: `docs/STRATEGY_SWITCHING.md` for complete guide

---

## 🔍 How They Work

Both bots follow the same pattern every 5 minutes:

1. **Fetch market data** - OHLCV, indicators, funding rates, OI
2. **Get open positions** - Query exchange for current positions
3. **AI decides** - Send all data to DeepSeek Chat → BUY/SELL/CLOSE/NOTHING
4. **Execute trade** - Place market order if decision is BUY/SELL/CLOSE

### Log Format (Lighter)
```
================================================================================
Decision Cycle - 2025-11-05 16:53:16
================================================================================

✅ Fetched metadata for 101 markets

📊 Raw positions from API:
  Exchange position: SOL (market_id=2) | LONG | size=0.061 | ...

MARKET DATA SUMMARY:
[Market data table with price, volume, funding, OI, indicators...]

🤖 LLM DECISION:
Action: BUY/SELL/CLOSE/NOTHING
Symbol: XYZ
Reasoning: [AI explanation]

✅ Order FILLED: avg_price=$X.XX
```

### Log Format (Pacifica)
```
INFO:__main__:║ 🤖 DECISION CYCLE START | 2025-11-07 15:14:27 | V2

Market Data (Latest):
BTC         $101,929.00     $685093K        N/A          87,297     62   +179.7         No
SOL             $160.06      $33453K        N/A       7,971,459     68     +0.8         No

[Decision 1/3]
  Symbol: DOGE
  Action: SELL
  Confidence: 0.78
  Reason: RSI 85 (extremely overbought)...

✅ ACCEPTED: SELL DOGE validated successfully
Order submitted: DOGE SELL 5.0
```

---

## 🧠 Shared Strategy System

**Location**: `llm_agent/llm/`

Both bots use the SAME AI brain:
- `model_client.py` - DeepSeek API calls
- `prompt_formatter.py` - Format market data for LLM
- `response_parser.py` - Parse LLM decisions
- `trading_agent.py` - Main decision logic

**DEX-specific code**:
- `lighter_agent/` - Lighter-specific data fetching & execution
- `pacifica_agent/` - Pacifica-specific data fetching & execution

**Shared infrastructure**:
- `trade_tracker.py` - Position tracking across both bots
- `config.py` - Global configuration

---

## ⚙️ Configuration

### Lighter API
- **Base**: `https://api.lighter.xyz`
- **Docs**: `https://apidocs.lighter.xyz`

### Pacifica API
- **Base**: `https://api.pacifica.fi/api/v1`
- **Key endpoints**:
  - `/kline` - OHLCV candles (5m interval)
  - `/book` - Orderbook
  - `/price` - Current prices
  - `/positions` - Account positions
  - `/orders/create_market` - Place orders

---

## 🛠️ Troubleshooting

### Bot not trading despite being "running"
1. Check if decision cycles are happening:
   ```bash
   tail -100 logs/<bot>.log | grep "Decision Cycle"
   ```

2. Check for errors:
   ```bash
   tail -100 logs/<bot>.log | grep -i "error\|failed"
   ```

3. Check for insufficient liquidity:
   ```bash
   tail -100 logs/<bot>.log | grep -i "liquidity"
   ```

4. Check for API rate limits:
   ```bash
   tail -100 logs/<bot>.log | grep -i "rate limit"
   ```

### DeepSeek API issues
- Check for rate limit errors in logs
- Verify API key in `.env`
- Check DeepSeek API status

### Market data shows N/A
- API parsing issue
- Check specific fetcher file:
  - Lighter: `lighter_agent/data/lighter_fetcher.py`
  - Pacifica: `pacifica_agent/data/pacifica_fetcher.py`

---

## 📁 Key Files

### Bot Entry Points
- `lighter_agent/bot_lighter.py` - Lighter bot main
- `pacifica_agent/bot_pacifica.py` - Pacifica bot main

### Shared AI Brain
- `llm_agent/llm/model_client.py` - LLM API calls
- `llm_agent/llm/trading_agent.py` - Decision logic
- `llm_agent/llm/prompt_formatter.py` - Data formatting
- `llm_agent/llm/response_parser.py` - Response parsing

### Data Fetching
- `lighter_agent/data/lighter_fetcher.py` - Lighter OHLCV
- `pacifica_agent/data/pacifica_fetcher.py` - Pacifica OHLCV
- `llm_agent/data/indicator_calculator.py` - RSI, MACD, EMA

### Trade Execution
- `lighter_agent/execution/trade_executor.py` - Lighter orders
- `pacifica_agent/execution/pacifica_executor.py` - Pacifica orders
- `trade_tracker.py` - Global position tracking

### Configuration
- `config.py` - Global settings
- `.env` - API keys

---

## 📚 Old Pacifica Bot (Archived)

The old Pacifica bot has been archived:
- **Location**: `archive/2025-10-30/live_pacifica.py.ARCHIVED`
- **Status**: Deprecated, use `pacifica_agent/` instead
- **Why archived**: Old infrastructure, replaced by modern `pacifica_agent/` following same pattern as Lighter bot

**Current Pacifica bot** (`pacifica_agent/`):
- ✅ Uses shared `llm_agent/llm/` strategy
- ✅ Same architecture as Lighter bot
- ✅ Comprehensive logging
- ✅ Dynamic symbol loading

---

**Last Updated**: 2025-11-07
