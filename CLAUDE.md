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

## Repository Navigation

**📍 START HERE**: See [`REPOSITORY_STRUCTURE.md`](REPOSITORY_STRUCTURE.md) for complete repository map with status indicators.

### Quick Navigation Tree

```
pacifica-trading-bot/
├── 📄 README.md                          # Project overview & quickstart
├── 📄 CLAUDE.md                          # ⭐ This file - development guide
├── 📄 REPOSITORY_STRUCTURE.md            # ⭐ Complete repo map & file index
├── 📄 PROGRESS.md                        # Session log
│
├── 🔧 SHARED INFRASTRUCTURE
│   ├── config.py                        # Global configuration
│   ├── trade_tracker.py                 # Trade tracking (used by LLM bot)
│   └── requirements.txt                 # Python dependencies
│
├── 🤖 ACTIVE BOT (ONLY ONE)
│   └── llm_agent/                       # ⭐ LLM Trading Bot (PID: 83713)
│       ├── bot_llm.py                   # Main entry point
│       ├── data/                        # Market data aggregation
│       ├── llm/                         # LLM decision logic
│       └── execution/                   # Trade execution
│
├── 📚 DOCUMENTATION
│   └── docs/
│       ├── DATA_SOURCES.md              # Complete API docs
│       ├── LLM_BOT_STATUS.md           # Current bot status
│       ├── DYNAMIC_TOKEN_ANALYSIS.md    # Token discovery docs
│       └── DEEP42_CUSTOM_QUERIES.md     # Deep42 macro queries
│
├── 🔬 RESEARCH (Organized by topic)
│   └── research/
│       ├── agent-lightning/             # Agent Lightning analysis
│       ├── moon-dev/                    # Moon Dev research
│       ├── funding-rates/               # Funding rate research
│       ├── strategies/                  # Strategy research
│       ├── cambrian/                    # Cambrian API research
│       └── lighter/                     # Lighter DEX research
│
├── 🛠️ UTILITIES
│   ├── dexes/                           # DEX SDKs (Pacifica, Lighter)
│   ├── scripts/                         # Testing/utility scripts
│   └── pacifica/                        # Pacifica integration
│
└── 🗄️ ARCHIVED (ALL OLD BOTS)
    └── archive/2025-10-30/
        ├── live_pacifica.py.ARCHIVED    # ⚠️ Old Pacifica bot
        ├── old-bot-infrastructure/      # Old bot supporting files
        ├── old-strategies/              # Old strategy implementations
        ├── old-bots/                    # Old bot executables
        └── old-scripts/                 # Old utility scripts
```

**Navigation Tips**:
- **Active bot**: `llm_agent/bot_llm.py` (PID: 83713) - THIS IS THE ONLY PRODUCTION BOT
- Bot status: `docs/LLM_BOT_STATUS.md`
- API docs: `docs/DATA_SOURCES.md`
- Research: `research/agent-lightning/` (latest)
- Full repo map: `REPOSITORY_STRUCTURE.md`

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

## Repository Structure

**Root Directory** (Clean & Minimal):
- `config.py` - ✅ SHARED - Global trading configuration
- `trade_tracker.py` - ✅ SHARED - Trade tracking (used by LLM bot)
- `requirements.txt` - ✅ SHARED - Python dependencies

**Active Bot** (ONLY ONE):
- `llm_agent/` - ✅ LLM Trading Bot (PID: 83713)
  - See "Current Active Bot" section below for details

**Documentation**:
- `docs/` - All project documentation
  - `DATA_SOURCES.md` - Complete API reference
  - `LLM_BOT_STATUS.md` - Current bot status
  - `DYNAMIC_TOKEN_ANALYSIS.md` - Token discovery
  - And more...

**Research** (Organized by topic):
- `research/agent-lightning/` - Agent Lightning analysis
- `research/moon-dev/` - Moon Dev research
- `research/funding-rates/` - Funding rate research
- `research/strategies/` - Strategy research
- `research/cambrian/` - Cambrian API research
- `research/lighter/` - Lighter DEX research

**Utilities**:
- `dexes/` - DEX SDKs (Pacifica, Lighter)
- `scripts/` - Testing and utility scripts
- `pacifica/` - Pacifica integration modules

**Archive** (ALL OLD BOTS):
- `archive/2025-10-30/` - Complete old bot archive
  - `live_pacifica.py.ARCHIVED` - Old Pacifica bot
  - `old-bot-infrastructure/` - Old infrastructure
  - `old-strategies/` - Old strategy implementations
  - `old-bots/` - Old bot executables
  - `old-scripts/` - Old utility scripts

**⚠️ CRITICAL**: Do NOT use any files in `archive/`. All old bots have been replaced by the LLM Trading Bot.

---

## Current Active Bot

**⚠️ ONLY ONE ACTIVE BOT - LLM Trading Bot**

**Bot**: `llm_agent/bot_llm.py` (PID: 7213)
**Mode**: LIVE (real trades)
**LLM Model**: DeepSeek Chat
**Strategy**: AI-driven decisions with Deep42 sentiment analysis
**Check Frequency**: Every 5 minutes (300 seconds)
**Position Size**: $30 per trade
**Max Positions**: 3
**Account**: Pacifica (8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc)

**Launch**:
```bash
# Live mode (real trades)
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &

# Dry-run mode (testing only)
nohup python3 -u -m llm_agent.bot_llm --dry-run --interval 300 > logs/llm_bot.log 2>&1 &
```

**Stop**:
```bash
pkill -f "llm_agent.bot_llm"
```

**Logs**: `logs/llm_bot.log` - All bot activity and decisions

**View Decision History**:
```bash
# Quick summary with action breakdown
python3 scripts/view_decisions.py

# Full detailed breakdown with Deep42 queries, token analyses, reasoning
python3 scripts/view_decision_details.py
```

**Decision Viewing Tools**:
- `scripts/view_decisions.py` - Quick summary of all decisions with stats
- `scripts/view_decision_details.py` - Complete breakdown showing:
  - 📊 Open positions count
  - 🔍 Custom Deep42 query generated
  - 🎯 Tokens selected for analysis
  - 📈 Token analyses completed
  - 💼 Position evaluations
  - 🤖 Final decision (BUY/SELL/CLOSE/NOTHING)
  - 📝 Complete reasoning
  - 💰 API cost
  - ⚡ Execution result

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
