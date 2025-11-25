# Trading Bot - Claude Development Guide

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
**API Key**: `doug.ZbEScx8M4zlf7kDn`
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
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn" \
  -H "Content-Type: application/json"
```

**Important**:
- API key header: `-H "X-API-Key: doug.ZbEScx8M4zlf7kDn"`
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
**Account Index**: `126039`
**API Key Index**: `3`

**API Keys** (from .env):
- Public: `0x25c2a6a1482466ba1960d455c0d2f41f09a24d394cbaa8d7b7656ce73dfff244faf638580b44e7d9`
- Private: `f4d86e544be209ed8926ec0f8eb162e6324dd69ab72e4e977028d07966678b18c5d42dc966247d49`

**Key Endpoints**:
- `/candlesticks` - Historical candle data (need to test intervals)
- Market data endpoints (via SDK)

**Fees**: ✅ **ZERO FEES**

---

## Current Strategies

See [strategies/README.md](strategies/README.md) for detailed strategy documentation including:
- Active strategies (Pacifica orderbook imbalance, Lighter VWAP)
- Entry/exit logic
- Risk/reward ratios
- Performance data
- Fee structures
- Future research

---

## Project Structure & Development Conventions

**CRITICAL**: This section MUST be updated EVERY time files are added, moved, or deleted.

### Directory Structure
```
pacifica-trading-bot/
├── bots/                    # Active bot executables
├── dexes/                   # DEX-specific SDKs
├── strategies/              # Strategy implementations
├── scripts/                 # One-off scripts and utilities
├── research/                # Research notes and analysis
├── archive/                 # Deprecated code (timestamped)
├── logs/                    # All log files (gitignored)
├── docs/                    # Documentation
├── config.py               # Global configuration
├── risk_manager.py         # Risk management
├── trade_tracker.py        # Trade tracking
└── README.md               # Project overview
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

## Active Bots

**Two autonomous trading bots** share the same LLM engine. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for complete details.

### Quick Bot Commands

**Lighter Bot** (zkSync, 101+ markets, zero fees):
```bash
# Check status
pgrep -f "lighter_agent.bot_lighter"

# Start/stop
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
pkill -f "lighter_agent.bot_lighter"

# Logs
tail -f logs/lighter_bot.log
```

**Pacifica Bot** (Solana, 4-5 liquid markets):
```bash
# Check status
pgrep -f "pacifica_agent.bot_pacifica"

# Start/stop
nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 > logs/pacifica_bot.log 2>&1 &
pkill -f "pacifica_agent.bot_pacifica"

# Logs
tail -f logs/pacifica_bot.log
```

**See [`USER_REFERENCE.md`](USER_REFERENCE.md) for complete command reference**

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
