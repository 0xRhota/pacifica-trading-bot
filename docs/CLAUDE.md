# Pacifica Trading Bot - Claude Instructions

## Project Overview

This is a **live trading bot** for Pacifica.fi (Solana perpetual derivatives exchange) that places REAL orders with REAL money. The bot is designed to look organic and profitable, not for volume farming.

## Critical Information

### Security
- **NEVER commit `.env` file** - contains Solana private key
- Private key stored in `.env` as `SOLANA_PRIVATE_KEY`
- Account address: `8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc`
- All sensitive data is gitignored

### Current Bot Configuration
```python
MIN_POSITION_SIZE_USD = 10.0   # Pacifica minimum requirement
MAX_POSITION_SIZE_USD = 15.0   # Conservative sizing for $150 account
MIN_PROFIT_THRESHOLD = 0.002   # 0.2% take profit
MAX_LOSS_THRESHOLD = 0.003     # 0.3% stop loss
MAX_LEVERAGE = 5.0             # Maximum leverage allowed
LOT_SIZE = 0.01                # Minimum order size increment

CHECK_FREQUENCY_SECONDS = 45   # How often to check positions
TRADE_FREQUENCY_SECONDS = 900  # 15 minutes between new positions
MAX_POSITION_HOLD_TIME = 1800  # 30 minute max hold

LONGS_ONLY = True              # Bull market mode
```

### Trading Symbols
- `SOL` - Solana
- `BTC` - Bitcoin
- `ETH` - Ethereum

## Repository Structure

```
pacifica-trading-bot/
├── Core Bot Files (root)
│   ├── live_bot.py          # Main live trading bot
│   ├── pacifica_sdk.py      # SDK for order placement & positions
│   ├── pacifica_bot.py      # API client for market data
│   ├── strategies.py        # Trading strategy logic
│   ├── risk_manager.py      # Risk management
│   ├── trade_tracker.py     # Trade logging & analytics
│   └── config.py            # Configuration settings
│
├── scripts/                 # Helper utilities
│   ├── place_order_now.py   # Test single order placement
│   ├── view_trades.py       # View trading statistics
│   ├── sync_tracker.py      # Sync tracker with API
│   └── check_status.sh      # Bot status check
│
├── docs/                    # Documentation
│   ├── CLAUDE.md            # AI development guide (this file)
│   ├── PROGRESS.md          # Development history
│   └── SETUP.md             # Original setup notes
│
├── archive/                 # Deprecated files (gitignored)
│   ├── main.py              # Original volume farming bot
│   ├── test_bot.py          # Early tests
│   └── ...                  # Other old files
│
├── Configuration Files
│   ├── README.md            # User-facing documentation
│   ├── .env                 # Private keys (GITIGNORED)
│   ├── .env.README          # Environment setup guide
│   ├── .gitignore           # Git ignore rules
│   └── requirements.txt     # Python dependencies
│
└── Data Files (gitignored)
    ├── trades.json          # Trade history
    ├── *.log                # Log files
    └── live_bot_output.log  # Current bot logs
```

## Architecture

### Core Files

**live_bot.py** - Main live trading bot
- Places real orders via SDK
- Monitors positions every 45s
- Opens new positions every 15min
- Auto-closes on profit/loss thresholds or time limits
- Integrates with trade tracker

**pacifica_sdk.py** - SDK wrapper for order placement
- Handles Solana wallet signing (Ed25519)
- Creates market orders with proper authentication
- `get_positions()` - Fetches current open positions
- Based on official Pacifica Python SDK

**pacifica_bot.py** - API interaction layer
- Fetches market data, prices, orderbooks
- Gets account information
- All endpoints use `/api/v1` base

**trade_tracker.py** - Trade logging and analytics
- Logs all entries and exits to `trades.json`
- Calculates P&L, win rate, statistics
- Persistent storage (gitignored)

**strategies.py** - Trading logic
- Orderbook-based decision making
- Bull market mode (longs only)
- Random position sizing within limits

**risk_manager.py** - Risk management
- Tracks daily P&L
- Enforces leverage limits
- Monitors position sizes

**config.py** - Central configuration
- All trading parameters
- API endpoints
- Account settings

### Helper Scripts

**place_order_now.py** - Test script for single orders
**view_trades.py** - View trading statistics and history
**sync_tracker.py** - Sync trade tracker with actual API positions
**check_status.sh** - Quick bot status check script

### Archived Files

Old test and development files moved to `archive/` directory:
- `main.py` - Original volume farming bot (deprecated)
- `test_bot.py` - Early testing script
- `test_live.py` - Live trading tests
- `dry_run_bot.py` - Dry run testing
- `place_test_order.py` - Order placement tests

## API Details

### Pacifica API Structure
```
Base URL: https://api.pacifica.fi/api/v1

GET  /book?symbol={symbol}       # Orderbook
GET  /price?symbol={symbol}      # Current price
GET  /account?address={addr}     # Account info (via pacifica_bot.py)
GET  /positions?account={addr}   # Open positions (via SDK)
POST /orders/create_market       # Place order (requires signature)
```

**Important**:
- Position data comes from `/positions?account={address}` endpoint
- Returns **net positions** (combined), not individual orders
- Use `pacifica_sdk.get_positions()` to fetch current positions

### Order Placement
Orders require Solana wallet signature using this structure:
```python
signature_header = {
    "timestamp": int(time.time() * 1000),
    "expiry_window": 5000,
    "type": "create_market_order"
}
signature_payload = {
    "symbol": "SOL",
    "amount": "0.05",
    "side": "bid",  # or "ask"
    "slippage_percent": "1.0"
}
```

## Known Issues & Fixes

### ✅ Position Monitoring Bug (FIXED - CRITICAL)
- **Issue**: Bot kept monitoring phantom positions after they were manually closed in UI
- **Cause**: Bot tracked positions in local dict, never checked API for external closes
- **Impact**: Would try to manage non-existent positions indefinitely
- **Fix**: Added API position syncing on startup and every check cycle
  - `_sync_positions_from_api()` - called on startup
  - `_check_and_manage_positions()` - verifies API positions every cycle
  - Detects externally closed positions and removes from tracking
- **Location**: live_bot.py:81-99, live_bot.py:101-114
- **Status**: Fixed and tested - bot now shows correct leverage (0.00x vs incorrect 0.17x)

### ✅ Position Sizing Bug (FIXED)
- **Issue**: First live order was 0.01 BTC (~$1,242) instead of $10-15
- **Cause**: Variable `actual_value` referenced before definition in fee calculation
- **Fix**: Added `actual_value = size * current_price` before usage + safety check
- **Location**: live_bot.py:188, live_bot.py:269
- **Status**: Fixed and tested

### ✅ Lot Size Requirements (SOLVED)
- All orders must be multiples of 0.01
- Must use `math.ceil(size / 0.01) * 0.01` to round UP
- Minimum order value: $10
- **Status**: Implemented and working

### ⚠️ API Connection Errors (MONITORING)
- Bot handles intermittent connection errors gracefully
- Retries on next check cycle (45s)
- Logs errors but continues running
- **Status**: Non-critical, normal operation

### 📝 Position Tracking Limitation (BY DESIGN)
- **Behavior**: Pacifica API returns net positions (combined), not individual orders
- **Example**: Two SOL orders (0.05 + 0.06) show as single 0.11 SOL position in API
- **Impact**: Trade tracker shows individual orders, but API shows combined
- **Workaround**: Use `sync_tracker.py` to reconcile with API
- **Status**: This is how Pacifica works, not a bug

## Running the Bot

### Start Live Trading
```bash
python3 live_bot.py
```

Bot runs in foreground. For background:
```bash
nohup python3 live_bot.py > live_bot_output.log 2>&1 &
```

### Monitor Activity
```bash
tail -f live_bot_output.log    # Live logs
python3 view_trades.py          # Statistics
```

### Check Status
```bash
ps aux | grep "python.*live_bot"  # Check if running
```

## Trade Tracking

All trades logged to `trades.json`:
```json
{
  "timestamp": "2025-10-06T20:52:28.926299",
  "order_id": "374951370",
  "symbol": "SOL",
  "side": "buy",
  "size": 0.05,
  "entry_price": 233.49,
  "exit_price": 233.00,
  "pnl": -0.0706,
  "pnl_pct": -0.0033,
  "fees": 0.0164,
  "status": "closed",
  "exit_reason": "Stop loss: -0.3315%"
}
```

## Development Workflow

1. **Before making changes**: Read relevant files
2. **Test changes**: Use `place_order_now.py` for single order tests
3. **Check logs**: Monitor `live_bot_output.log` for errors
4. **Verify positions**: Check Pacifica UI and trade tracker match
5. **Update docs**: Keep CLAUDE.md and PROGRESS.md current
6. **Commit**: Use descriptive commit messages

## Important Reminders

- Bot trades with REAL MONEY - test changes carefully
- Always verify `.env` is gitignored before commits
- Position sizes are intentionally small ($10-15) for safety
- Stop losses trigger at -0.3% to limit losses
- Check API for actual positions, don't trust tracker alone
- Bot auto-restarts needed after code changes

## Current Status

- **Bot Status**: ✅ LIVE TRADING (running in background)
- **Account Balance**: ~$145
- **Open Positions**: 2 (BTC and SOL)
  - BTC: 0.01 BTC @ $124,266
  - SOL: 0.11 SOL @ $233.35 (combined position)
- **Latest Trade**: Order #375064273 (SOL) - **FIRST WINNER!** +$0.02
- **Win Rate**: 25% (1 win, 3 losses)
- **Total P&L**: -$1.31

## Future Improvements

- [ ] Better position sizing algorithm
- [ ] More sophisticated entry signals
- [ ] Dynamic stop loss based on volatility
- [ ] Multiple position management
- [ ] Web dashboard for monitoring
- [ ] Backtesting framework
- [ ] Alert system for errors
