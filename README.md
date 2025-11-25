# Pacifica Trading Bot

AI-powered perpetual futures trading system for Pacifica (Solana) and Lighter (zkSync) DEXs.

## Current Status
- ✅ **Lighter Bot**: AI-driven trading with Deep42 intelligence (LIVE)
- ✅ **Pacifica Bot**: AI-driven swing trading (Available)
- 🧠 **LLM Engine**: DeepSeek Chat with multi-timeframe market context

## Quick Start

```bash
# Check bot status
pgrep -f "bot_lighter"     # Lighter bot PID
pgrep -f "bot_pacifica"    # Pacifica bot PID

# View live logs
tail -f logs/lighter_bot.log
tail -f logs/pacifica_bot.log

# Start bots
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 > logs/pacifica_bot.log 2>&1 &

# Stop bots
pkill -f "lighter_agent.bot_lighter"
pkill -f "pacifica_agent.bot_pacifica"
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system architecture and design
- **[USER_REFERENCE.md](USER_REFERENCE.md)** - Quick command reference
- **[CLAUDE.md](CLAUDE.md)** - Development guide (for Claude Code)
- **[AGENTS.md](AGENTS.md)** - AI agent collaboration guide

## System Overview

**Two autonomous trading bots** share a common LLM-based decision engine:

1. **Lighter Bot** (`lighter_agent/`)
   - zkSync (fee-less perpetual futures)
   - 101+ markets dynamically loaded
   - V1 prompt with Deep42 multi-timeframe integration
   - Profit-focused volume generation

2. **Pacifica Bot** (`pacifica_agent/`)
   - Solana (Pacifica DEX)
   - 4-5 liquid markets (BTC, SOL, ETH, DOGE)
   - V2 deep reasoning prompt
   - Swing trading strategy

**Shared Infrastructure**:
- `llm_agent/llm/` - LLM decision engine (DeepSeek Chat)
- `llm_agent/data/` - Market data and indicators
- `dexes/` - Exchange SDKs
- `config.py` - Global configuration
- `trade_tracker.py` - Position tracking

**See [ARCHITECTURE.md](ARCHITECTURE.md) for complete details**

---

## How It Works

Both bots follow the same pattern every 5 minutes:

1. **Fetch Market Data** - OHLCV, indicators (RSI, MACD, EMA), funding rates, open interest
2. **Get Deep42 Context** - Multi-timeframe market intelligence (regime, BTC health, macro)
3. **Get Open Positions** - Query exchange for current positions
4. **LLM Decision** - Send all context to DeepSeek Chat → BUY/SELL/CLOSE/NOTHING
5. **Execute Trade** - Place market orders based on LLM decision

**Key Feature**: No hard-coded rules - the LLM makes autonomous decisions based on comprehensive market context.

---

## Environment Setup

Required environment variables in `.env`:

```bash
# DeepSeek LLM
DEEPSEEK_API_KEY=<your_key>

# Cambrian Network (Deep42)
CAMBRIAN_API_KEY=<your_key>

# Lighter DEX
LIGHTER_PRIVATE_KEY=<hex_key>
LIGHTER_API_KEY_PUBLIC=<public_key>
LIGHTER_API_KEY_PRIVATE=<private_key>

# Pacifica (Solana)
SOLANA_PRIVATE_KEY=<base58_key>
```

---

## Performance Tracking

View trade history and P&L:

```bash
# Export trades to CSV
python3 scripts/export_trades.py

# View trade statistics
python3 -c "from trade_tracker import TradeTracker; t = TradeTracker(); t.print_summary()"
```

---

## Development

- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Development Guide**: See [CLAUDE.md](CLAUDE.md)
- **Agent Collaboration**: See [AGENTS.md](AGENTS.md)
