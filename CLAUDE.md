# Trading Bot - Claude Development Guide

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

### Root Infrastructure (imported everywhere)
- `config.py` - Trading configuration, lot sizes, market IDs
- `pacifica_bot.py` - PacificaAPI wrapper for market data
- `risk_manager.py` - Position sizing and risk controls
- `trade_tracker.py` - Trade tracking and P&L calculation
- `.env` - Environment variables and API keys

### Bots (`bots/`)
Live trading bots that execute strategies:
- `vwap_lighter_bot.py` - ✅ **ACTIVE** - VWAP strategy on Lighter DEX (6 symbols, 5-min checks)

**Import pattern**: Add path to root
```python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Strategies (`strategies/`)
Trading strategy implementations:
- `base_strategy.py` - Abstract base class for all strategies
- `vwap_strategy.py` - ✅ **ACTIVE** - VWAP + Orderbook imbalance (long/short)
- `basic_long_only.py` - 📦 Archived - Original long-only strategy
- `long_short.py` - 🚧 Work in progress

### DEX SDKs (`dexes/`)
Exchange-specific SDK wrappers:
- `lighter/lighter_sdk.py` - Lighter DEX SDK (BTC=1, SOL=2, ETH=3, PENGU=4, XPL=5, ASTER=6)
  - `create_market_order()` - Market orders (working)
  - `create_stop_loss_order()` - Stop-loss protection
  - `create_take_profit_order()` - Take-profit targets
  - `get_balance()` - Account balance
  - `get_positions()` - Open positions

### Utilities (`utils/`)
Shared utility functions:
- `vwap.py` - Session VWAP calculation (midnight UTC reset, typical price formula)
- `logger.py` - Logging configuration

### Scripts (`scripts/`)
Testing and utility scripts organized by purpose:

**Lighter Scripts** (`scripts/lighter/`):
- `check_account.py` - Check account details
- `check_balance.py` - Check account balance
- `explore_sdk.py` - Explore SDK capabilities
- `find_account_index.py` - Find account index
- `find_api_key.py` - Find API key
- `get_account_index.py` - Get account index
- `register_api_key.py` - Register API key
- `setup_api_key.py` - Setup API key
- `test_connection.py` - Test Lighter connection
- `test_order.py` - Test order placement
- `test_trade.py` - Test trade execution

**General Scripts** (`scripts/general/`):
- `sync_tracker.py` - Sync trade tracker with exchange
- `place_order_now.py` - Manual order placement

**Import pattern for scripts**: Two levels up
```python
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
```

### Research (`research/`)
Strategy research, backtesting, and market analysis

### Archive (`archive/`)
Deprecated files kept for reference:
- `live_bot.py` - Original Pacifica-only bot
- `live_bot_lighter.py` - First Lighter bot attempt

**Note**: Do not import from archived files

---

## Current Active Bot

**Bot**: `bots/vwap_lighter_bot.py`
**Strategy**: VWAP + Orderbook Imbalance (1.3x threshold)
**Symbols**: BTC, SOL, ETH, PENGU, XPL, ASTER
**Check Frequency**: Every 5 minutes
**Position Size**: $20 per trade
**Stop Loss**: 1%
**Take Profit**: 2.5%
**Max Hold**: 60 minutes
**Account**: Lighter (126039) - $433.99 balance

**Launch**:
```bash
python3 bots/vwap_lighter_bot.py
# Or background:
nohup python3 -u bots/vwap_lighter_bot.py > vwap_bot_output.log 2>&1 &
```

**Stop**:
```bash
pkill -f vwap_lighter_bot
```
