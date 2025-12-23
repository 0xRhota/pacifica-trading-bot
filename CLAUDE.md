# Hopium Agents - AI Agent Guide

## 🎯 Core Mission (Original Tweet)

**"We feed them a variety of quantitative data that tries to capture the 'state' of the market at different granularities. Funding rates, OI, volume, RSI, MACD, EMA, etc"**

This bot MUST track and display ALL of these data sources in every decision:
- ✅ **Funding rates** - Perpetual futures funding (long/short bias)
- ✅ **Open Interest (OI)** - Total open positions (market leverage)
- ✅ **Volume** - 24h trading volume (liquidity/momentum)
- ✅ **RSI** - Relative Strength Index (overbought/oversold)
- ✅ **MACD** - Moving Average Convergence Divergence (trend strength)
- ✅ **EMA/SMA** - Exponential/Simple Moving Averages (trend direction)
- ✅ **Deep42 Sentiment** - AI-powered market intelligence
- ✅ **Price** - Current spot price

**Every decision cycle MUST log this data summary BEFORE the LLM decision.**

---

## System Architecture

**📍 REPOSITORY STRUCTURE**: See [`ARCHITECTURE.md`](ARCHITECTURE.md) for complete system architecture, bot details, and file organization.

### Quick Navigation
- **Architecture Overview**: [`ARCHITECTURE.md`](ARCHITECTURE.md) - Complete system design
- **Bot Commands**: [`USER_REFERENCE.md`](USER_REFERENCE.md) - Quick command reference
- **API Documentation**: [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) - API endpoints and usage
- **Agent Guide**: [`AGENTS.md`](AGENTS.md) - For AI agents collaborating on this codebase

---

## Development Guidelines

**IMPORTANT**:
- Never provide time estimates (e.g., "30 minutes", "2 hours", "3 days") in responses
- Time estimates have no bearing on development work and should be omitted
- Focus on what needs to be done, not how long it might take

**CRITICAL - Blockchain Addresses**:
- NEVER truncate, abbreviate, or test with partial blockchain addresses (e.g., "0x023a..." or "0xabcd")
- ALWAYS use complete, full-length addresses when querying APIs
- Partial addresses will return incorrect/empty data and waste debugging time
- If an address is unknown, search for the full address first before querying

---

## Consulting Qwen (LLM API)

To ask Qwen questions about trading strategy, performance, etc:

```python
import requests
import os
from dotenv import load_dotenv
load_dotenv('.env')

api_key = os.getenv('OPEN_ROUTER')
response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "qwen/qwen-2.5-72b-instruct",  # or qwen/qwen3-32b
        "messages": [
            {"role": "system", "content": "You are an expert quant trader."},
            {"role": "user", "content": "YOUR QUESTION HERE"}
        ],
        "max_tokens": 800
    }
)
print(response.json()['choices'][0]['message']['content'])
```

**Key**: `OPEN_ROUTER` in `.env`
**Models**: `qwen/qwen-2.5-72b-instruct` (best), `qwen/qwen3-32b` (reasoning mode)

## Data Sources & APIs

### Pacifica API
**Base URL**: `https://api.pacifica.fi/api/v1`
**Account**: `8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc`

**Key Endpoints**:
- `/kline` - OHLCV candle data
- `/book` - Orderbook (real-time)
- `/price` - Current prices
- `/positions` - Account positions
- `/orders/create_market` - Place orders (requires signature)

**Candle Intervals Available**: 1m, 3m, 5m, **15m**, 30m, 1h, 2h, 4h, 8h, 12h, 1d

**Example - Get 15m candles**:
```bash
curl "https://api.pacifica.fi/api/v1/kline?symbol=SOL&interval=15m&start_time=1759860000000&limit=10"
```

**Data Freshness Test Results**:
- 15m candles: ✅ **UP-TO-DATE** (0.025% divergence from live orderbook)
- Orderbook: ✅ **INSTANT** (<1 second latency)
- **Verdict**: Use 15m candles for VWAP/trend, orderbook for entry timing

---

### Cambrian API
**Base URL**: `https://opabinia.cambrian.network/api/v1`
**API Key**: Set `CAMBRIAN_API_KEY` in `.env`
**Docs Pattern**: Each endpoint has `/llms.txt` for AI-readable docs

**Key Endpoints**:
- `/solana/ohlcv/token` - Token OHLCV data
- `/solana/ohlcv/pool` - Pool OHLCV data
- `/solana/ohlcv/base-quote` - Base/quote pair OHLCV

**Documentation**:
- Main: `https://docs.cambrian.org/api/v1/solana/ohlcv/token`
- LLM Docs: `https://docs.cambrian.org/api/v1/solana/ohlcv/token/llms.txt`

**Example - Get 15m OHLCV data**:
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/ohlcv/token?token_address=So11111111111111111111111111111111111111112&after_time=1759858000&before_time=1759865709&interval=15m" \
  -H "X-API-Key: $CAMBRIAN_API_KEY" \
  -H "Content-Type: application/json"
```

**Important**:
- API key header: `-H "X-API-Key: $CAMBRIAN_API_KEY"`
- Uses Unix timestamps (seconds, not milliseconds)
- Response format: ClickHouse columnar format (columns + data array)

**Response Format**:
```json
[{
  "columns": [
    {"name": "openPrice", "type": "Nullable(Float64)"},
    {"name": "closePrice", "type": "Nullable(Float64)"},
    ...
  ],
  "data": [
    [235.44, 235.54, ...],  // Row 1
    [235.38, 235.39, ...]   // Row 2
  ],
  "rows": 25
}]
```

**Data Freshness Test Results**:
- 15m candles: ✅ **FRESH** (5 min old, 0.046% divergence from Pacifica)
- Aligned with Pacifica within 0.05%
- **Verdict**: Both Pacifica and Cambrian candles are UP-TO-DATE

**Token Addresses**:
- SOL: `So11111111111111111111111111111111111111112`
- Need to look up BTC/ETH wrapped token addresses on Solana

---

### Lighter DEX API
**Base URL**: `https://api.lighter.xyz`
**Docs**: `https://apidocs.lighter.xyz`
**API Keys**: Set `LIGHTER_PUBLIC_KEY` and `LIGHTER_PRIVATE_KEY` in `.env`

**Key Endpoints**:
- `/candlesticks` - Historical candle data (need to test intervals)
- Market data endpoints (via SDK)

**Fees**: ✅ **ZERO FEES**

---

## Current Strategies

Strategy history is tracked in `logs/strategy_switches.log`. The LLM prompt IS the strategy - we've iterated through 17 versions so far. See the README for highlights.

---

## Project Structure & Development Conventions

**CRITICAL**: This section MUST be updated EVERY time files are added, moved, or deleted.

### Directory Structure
```
hopium-agents/
├── hibachi_agent/           # Hibachi exchange adapter
├── lighter_agent/           # Lighter exchange adapter
├── extended_agent/          # Extended Lighter adapter
├── pacifica_agent/          # Pacifica exchange adapter
├── llm_agent/               # Shared strategy engine
│   ├── llm/                 # LLM integration
│   ├── data/                # Market data fetchers
│   └── prompts_archive/     # Historical prompts
├── dexes/                   # Exchange SDKs
├── research/                # Research and experiments
├── scripts/                 # Utility scripts
├── logs/                    # Trade logs (gitignored)
├── config.py                # Global configuration
├── trade_tracker.py         # Trade tracking
└── README.md                # Project overview
```

### File Naming Conventions

**Bots**: `bots/<dex>_<strategy>_bot.py`
- Examples: `bots/vwap_lighter_bot.py`, `bots/live_pacifica.py`

**Logs**: `logs/<bot_name>.log`
- Current active: `logs/<bot_name>.log`
- Historical: `logs/<bot_name>_2025-01-07.log`

**Strategies**: `strategies/<strategy_name>.py`
- Examples: `strategies/vwap_strategy.py`, `strategies/long_short.py`

### Git Practices

**What to Commit**:
- ✅ Source code (`.py`)
- ✅ Documentation (`.md`)
- ✅ Configuration templates (`.env.example`)
- ✅ Requirements (`requirements.txt`)

**What to Ignore**:
- ❌ Log files (`*.log`)
- ❌ Secrets (`.env`, `*key*`, `*secret*`)
- ❌ Python cache (`__pycache__/`, `*.pyc`)
- ❌ IDE files (`.vscode/`, `.idea/`)

### Deprecation Process

When replacing old code:
1. Move to `archive/<YYYY-MM-DD>/`
2. Add comment in replacement with reference
3. Update documentation

### Log Management

- Bots MUST write to `logs/` directory only
- Use log rotation (max 7 days or 100MB)
- Never commit logs to git
- Use structured logging with timestamps

### Code Review Standards

Before any production deployment:
- [ ] No secrets in code
- [ ] Logs go to `logs/` directory
- [ ] Error handling on all API calls
- [ ] Type hints on public functions
- [ ] Docstrings on all classes/functions

---

## Agent Commands

All agents use the same centralized strategy system in `llm_agent/`. The exchange-specific code handles data fetching and order execution.

```bash
# Check what's running
ps aux | grep -E "(hibachi|lighter|extended|pacifica)_agent"

# View logs
tail -f logs/hibachi_bot.log
tail -f logs/lighter_bot.log
tail -f logs/extended_bot.log

# Stop an agent
pkill -f "hibachi_agent.bot_hibachi"
pkill -f "lighter_agent.bot_lighter"
pkill -f "extended_agent.bot_extended"

# Start agents
nohup python3 -u -m hibachi_agent.bot_hibachi --live --interval 600 > logs/hibachi_bot.log 2>&1 &
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
nohup python3.11 -u -m extended_agent.bot_extended --live --strategy C --interval 300 > logs/extended_bot.log 2>&1 &
```

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
