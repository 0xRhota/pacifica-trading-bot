# Trading Bot - System Architecture

**Purpose**: This document describes the complete system architecture for humans and AI agents working on this codebase.

---

## 🏗️ System Overview

This project runs **two autonomous trading bots** that share a common LLM-based decision engine:

1. **Lighter Bot** (`lighter_agent/`) - Trades on Lighter DEX (zkSync)
2. **Pacifica Bot** (`pacifica_agent/`) - Trades on Pacifica (Solana)

Both bots use **DeepSeek Chat** as their AI brain and share core infrastructure for:
- Market data processing
- Technical indicator calculation
- LLM decision-making
- Trade tracking

---

## 📁 Repository Structure

```
pacifica-trading-bot/
├── 📄 README.md                          # Project overview
├── 📄 ARCHITECTURE.md                    # ⭐ This file - system architecture
├── 📄 CLAUDE.md                          # Development guide (for Claude Code)
├── 📄 AGENTS.md                          # AI agent collaboration guide
├── 📄 USER_REFERENCE.md                  # Quick reference (for human user)
├── 📄 PROGRESS.md                        # Session log
│
├── 🔧 SHARED INFRASTRUCTURE
│   ├── config.py                        # Global configuration
│   ├── trade_tracker.py                 # Trade tracking (used by both bots)
│   └── requirements.txt                 # Python dependencies
│
├── 🤖 LIGHTER BOT
│   └── lighter_agent/
│       ├── bot_lighter.py              # Main entry point
│       ├── data/
│       │   ├── lighter_aggregator.py   # Market data aggregation
│       │   └── lighter_fetcher.py      # Lighter API data fetching
│       └── execution/
│           └── lighter_executor.py     # Order execution
│
├── 🤖 PACIFICA BOT
│   └── pacifica_agent/
│       ├── bot_pacifica.py             # Main entry point
│       ├── data/
│       │   ├── pacifica_aggregator.py  # Market data aggregation
│       │   └── pacifica_fetcher.py     # Pacifica API data fetching
│       └── execution/
│           └── pacifica_executor.py    # Order execution
│
├── 🧠 SHARED LLM ENGINE
│   └── llm_agent/
│       ├── llm/
│       │   ├── trading_agent.py                        # LLM orchestration
│       │   ├── model_client.py                         # DeepSeek API client
│       │   ├── prompt_formatter.py                     # V1 prompt (Lighter)
│       │   ├── prompt_formatter_v2_deep_reasoning.py   # V2 prompt (Pacifica)
│       │   └── response_parser.py                      # LLM response parsing
│       ├── data/
│       │   ├── indicator_calculator.py                 # RSI, MACD, EMA
│       │   ├── macro_fetcher.py                        # Deep42 macro context
│       │   └── oi_fetcher.py                          # Open interest data
│       └── config_prompts.py                          # Prompt version switching
│
├── 🔌 EXCHANGE SDKS
│   └── dexes/
│       ├── pacifica/
│       │   ├── pacifica_sdk.py         # Pacifica order placement
│       │   └── adapter.py              # Pacifica data adapter
│       └── lighter/
│           └── lighter_sdk.py          # Lighter order placement
│
├── 📚 DOCUMENTATION
│   └── docs/
│       ├── DATA_SOURCES.md             # Complete API reference
│       ├── BOT_STATUS.md               # Bot commands & status
│       ├── STRATEGY_MANAGEMENT.md      # Strategy documentation
│       └── DATA_SOURCES_SUMMARY.md     # Data source summary
│
├── 🔬 RESEARCH (Organized by topic)
│   └── research/
│       ├── DEEP42_*.md                 # Deep42 integration docs
│       ├── pacifica/                   # Pacifica-specific research
│       ├── lighter/                    # Lighter DEX research
│       ├── agent-lightning/            # Agent Lightning analysis
│       ├── moon-dev/                   # Moon Dev research
│       ├── funding-rates/              # Funding rate research
│       ├── strategies/                 # Strategy research
│       └── cambrian/                   # Cambrian API research
│
├── 🛠️ UTILITIES
│   ├── scripts/                        # Testing/utility scripts
│   └── utils/                         # Shared utilities
│
├── 🗄️ LOGS (gitignored)
│   └── logs/
│       ├── lighter_bot.log            # Lighter bot logs
│       ├── pacifica_bot.log           # Pacifica bot logs
│       └── trades/                    # Trade data exports
│
└── 🗄️ ARCHIVED (Deprecated code)
    └── archive/
        └── 2025-*/                    # Timestamped archives
```

---

## 🤖 Active Bots

### Lighter Bot
**File**: `lighter_agent/bot_lighter.py`
**Exchange**: Lighter DEX (zkSync)
**Markets**: 101+ dynamically loaded (BTC, SOL, ETH, DOGE, PENGU, etc.)
**Fees**: Zero
**Position Size**: $5 per trade
**Max Positions**: 15
**Interval**: 5 minutes (300 seconds)
**Account**: 341823 (API Key Index: 2)

**Features**:
- Zero-fee trading (fee-less DEX)
- 101+ perpetual futures markets
- V1 prompt with Enhanced Deep42 integration (multi-timeframe)
- Dynamic symbol discovery

**Status Check**:
```bash
pgrep -f "lighter_agent.bot_lighter"
tail -f logs/lighter_bot.log
```

### Pacifica Bot
**File**: `pacifica_agent/bot_pacifica.py`
**Exchange**: Pacifica (Solana)
**Markets**: BTC, SOL, ETH, DOGE (liquid markets only)
**Fees**: 0.04% taker fee
**Position Size**: $250-500 notional ($5-10 margin @ 50x leverage)
**Max Positions**: 15
**Interval**: 5 minutes (300 seconds)
**Account**: `8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc`

**Features**:
- High leverage trading (up to 50x)
- Lower fees than most CEXs
- V2 Deep Reasoning prompt
- Swing trading strategy

**Status Check**:
```bash
pgrep -f "pacifica_agent.bot_pacifica"
tail -f logs/pacifica_bot.log
```

---

## 🧠 Shared LLM Engine

Both bots share the same AI decision-making infrastructure:

### Core Components

**`llm_agent/llm/trading_agent.py`** - LLM Orchestration
- Manages LLM API calls
- Coordinates prompt formatting and response parsing
- Handles retries and error recovery

**`llm_agent/llm/model_client.py`** - DeepSeek API Client
- API request handling with rate limiting
- Token usage tracking
- Daily spend limit enforcement ($10/day shared across both bots)

**`llm_agent/llm/prompt_formatter.py`** - V1 Prompt (Lighter)
- Formats market data for LLM
- Includes Deep42 multi-timeframe context (1h regime, 4h BTC health, 6h macro)
- DEX-specific instructions (Lighter: profit-focused volume)

**`llm_agent/llm/prompt_formatter_v2_deep_reasoning.py`** - V2 Prompt (Pacifica)
- Enhanced reasoning format
- More detailed decision explanations
- DEX-specific instructions (Pacifica: swing trading with fees)

**`llm_agent/llm/response_parser.py`** - Response Parsing
- Extracts BUY/SELL/CLOSE/NOTHING decisions
- Validates symbol availability
- Parses confidence scores and reasoning

### Data Processing

**`llm_agent/data/indicator_calculator.py`** - Technical Indicators
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- EMA/SMA (Exponential/Simple Moving Averages)
- Volume analysis

**`llm_agent/data/macro_fetcher.py`** - Deep42 Integration
- Market regime analysis (1-hour cache)
- BTC health indicator (4-hour cache)
- Macro context (6-hour cache)
- Multi-timeframe context aggregation

**`llm_agent/data/oi_fetcher.py`** - Open Interest Data
- Perpetual futures open interest
- Market leverage analysis

### Strategy Configuration

**`llm_agent/config_prompts.py`** - Prompt Version Management
- V1 (original) - Lighter bot
- V2 (deep reasoning) - Pacifica bot
- Easy switching without code changes

---

## 🔌 Exchange Integration

### Lighter DEX (zkSync)
**SDK**: `dexes/lighter/lighter_sdk.py`
**Data Fetcher**: `lighter_agent/data/lighter_fetcher.py`
**Base URL**: `https://api.lighter.xyz`
**Docs**: `https://apidocs.lighter.xyz`

**Key Features**:
- Zero fees (fee-less perpetual futures)
- 101+ markets
- Real-time candlestick data
- WebSocket support for live updates

### Pacifica (Solana)
**SDK**: `dexes/pacifica/pacifica_sdk.py`
**Data Fetcher**: `pacifica_agent/data/pacifica_fetcher.py`
**Base URL**: `https://api.pacifica.fi/api/v1`

**Key Endpoints**:
- `/kline` - OHLCV candle data
- `/book` - Orderbook (real-time)
- `/price` - Current prices
- `/positions` - Account positions
- `/orders/create_market` - Place orders (requires signature)

---

## 🔄 Decision Cycle Flow

Both bots follow the same pattern every 5 minutes:

```
┌─────────────────────────────────────────────────────────────────┐
│                     DECISION CYCLE START                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. FETCH MARKET DATA                                            │
│     - OHLCV candles (15m interval)                              │
│     - Current prices                                             │
│     - 24h volume                                                 │
│     - Funding rates (if available)                               │
│     - Open interest (if available)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. CALCULATE INDICATORS                                         │
│     - RSI (Relative Strength Index)                             │
│     - MACD (Moving Average Convergence Divergence)               │
│     - EMA20 (20-period Exponential Moving Average)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. FETCH DEEP42 CONTEXT (Multi-Timeframe)                      │
│     - Market regime (1h cache) - Risk-on/Risk-off                │
│     - BTC health (4h cache) - Long/Short bias                    │
│     - Macro context (6h cache) - Overall market state            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. GET OPEN POSITIONS                                           │
│     - Query exchange API for current positions                   │
│     - Calculate unrealized P&L                                   │
│     - Check position staleness (auto-close if > 240 min)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. FORMAT PROMPT                                                │
│     - Market data table                                          │
│     - Open positions                                             │
│     - Deep42 intelligence                                        │
│     - DEX-specific instructions                                  │
│     - Trade history review                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. LLM DECISION (DeepSeek Chat)                                 │
│     - Analyze all context                                        │
│     - Generate BUY/SELL/CLOSE/NOTHING decisions                  │
│     - Provide confidence score (0.0-1.0)                         │
│     - Explain reasoning                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. VALIDATE DECISION                                            │
│     - Check symbol availability                                  │
│     - Verify position limits (max 15)                            │
│     - Validate confidence threshold                              │
│     - Ensure no duplicate positions                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. EXECUTE TRADE                                                │
│     - BUY: Open new long position                                │
│     - SELL: Open new short position                              │
│     - CLOSE: Close existing position                             │
│     - NOTHING: Skip this cycle                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. LOG RESULT                                                   │
│     - Decision details                                           │
│     - Order execution status                                     │
│     - P&L if closing position                                    │
│     - Update trade tracker                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Wait 5 minutes, repeat
```

---

## 🔒 Shared Infrastructure

### Trade Tracking
**File**: `trade_tracker.py`

Tracks all open positions across both bots:
- Position entry time and price
- Current P&L
- Position staleness
- Trade history

Both bots write to the same tracker to maintain global position awareness.

### Configuration
**File**: `config.py`

Global settings shared by both bots:
- Position sizing
- Risk limits
- API endpoints
- Logging configuration

### Rate Limiting
**File**: `utils/shared_rate_limiter.py`

Coordinated rate limiting across both bots to prevent API throttling.

---

## 📊 Data Sources

### Cambrian Network (Deep42)
**Purpose**: AI-powered market intelligence
**Endpoint**: `https://deep42.cambrian.network`
**Usage**:
- Market regime analysis (risk-on/risk-off)
- BTC health indicator
- Social sentiment quality scores
- On-chain analysis

**Caching**:
- Regime: 1 hour
- BTC health: 4 hours
- Macro: 6 hours

### Open Interest Data
**Purpose**: Market leverage and positioning
**Sources**:
- Exchange APIs (when available)
- Cambrian Network fallback

### Funding Rates
**Purpose**: Long/short bias indicator
**Sources**:
- Lighter DEX (via SDK)
- Pacifica (via API)

---

## 🎯 Bot Strategies

### Lighter Bot (V1 Prompt)
**Strategy**: Profit-focused volume generation
**Philosophy**:
- PRIMARY: Make profitable trades (55%+ win rate, 2:1 R:R minimum)
- SECONDARY: Generate volume for airdrop eligibility
- NEVER sacrifice profit for volume

**Key Features**:
- Zero fees enable high-frequency quality trades
- Deep42 regime-aware decisions (risk-on vs risk-off)
- Pump-and-dump filtering (quality score < 5 = skip)
- Strict 2% profit / 1% loss targets

### Pacifica Bot (V2 Prompt)
**Strategy**: Swing trading with deep reasoning
**Philosophy**:
- Hold positions longer (4-24 hours)
- Higher confidence threshold
- Fee-conscious (0.04% per trade)
- Detailed reasoning for each decision

**Key Features**:
- 50x leverage for capital efficiency
- Swing trading on 4-5 liquid markets
- Deep reasoning format for better decisions
- Fee optimization

---

## 🔧 Development Patterns

### Adding a New Bot
1. Create `<name>_agent/` directory
2. Implement bot entry point following existing pattern
3. Create `data/` subdirectory for fetchers
4. Create `execution/` subdirectory for executor
5. Update `ARCHITECTURE.md` and `AGENTS.md`

### Adding a New Prompt Version
1. Create new formatter in `llm_agent/llm/`
2. Add version to `config_prompts.py`
3. Test with dry-run mode
4. Document strategy in this file

### Modifying Shared Infrastructure
⚠️ **CRITICAL**: Changes to `llm_agent/` affect BOTH bots
- Test thoroughly before deploying
- Consider impact on both Lighter and Pacifica
- Update logs to track which bot made the change

---

## 📝 File Ownership

### Bot-Specific (Safe to modify)
- `lighter_agent/*` - Lighter bot only
- `pacifica_agent/*` - Pacifica bot only
- `dexes/lighter/*` - Lighter SDK only
- `dexes/pacifica/*` - Pacifica SDK only

### Shared (Requires coordination)
- `llm_agent/*` - Used by BOTH bots
- `config.py` - Global configuration
- `trade_tracker.py` - Shared tracking
- `utils/*` - Shared utilities

### Documentation (Keep updated)
- `ARCHITECTURE.md` - This file
- `CLAUDE.md` - Development guide
- `AGENTS.md` - Agent collaboration
- `USER_REFERENCE.md` - Quick reference

---

## 🚀 Quick Start

### Start Both Bots
```bash
# Lighter (live)
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &

# Pacifica (live)
nohup python3 -u -m pacifica_agent.bot_pacifica --live --interval 300 > logs/pacifica_bot.log 2>&1 &
```

### Monitor Both Bots
```bash
# Check status
pgrep -f "bot_lighter"
pgrep -f "bot_pacifica"

# View logs
tail -f logs/lighter_bot.log
tail -f logs/pacifica_bot.log
```

### Stop Both Bots
```bash
pkill -f "lighter_agent.bot_lighter"
pkill -f "pacifica_agent.bot_pacifica"
```

---

**Last Updated**: 2025-11-13 (Deep42 multi-timeframe integration deployed)
**Maintained By**: Claude Code (Sonnet 4.5)
