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
**test_bot.py** - Original testing script (deprecated)

## API Details

### Pacifica API Structure
```
Base URL: https://api.pacifica.fi/api/v1

GET /book?symbol={symbol}     # Orderbook
GET /price?symbol={symbol}    # Current price
GET /account?address={addr}   # Account info
POST /order                   # Place order (requires signature)
```

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

### Position Sizing Bug (FIXED)
- **Issue**: First live order was 0.01 BTC (~$1,242) instead of $10-15
- **Cause**: Variable `actual_value` referenced before definition in fee calculation
- **Fix**: Added `actual_value = size * current_price` before usage + safety check
- **Location**: live_bot.py:188, live_bot.py:269

### Lot Size Requirements
- All orders must be multiples of 0.01
- Must use `math.ceil(size / 0.01) * 0.01` to round UP
- Minimum order value: $10

### API Connection Errors
- Bot handles intermittent connection errors gracefully
- Retries on next check cycle (45s)
- Logs errors but continues running

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

- **Bot Status**: Running (PID check required)
- **Account Balance**: ~$145
- **Latest Trade**: Order #375064273 (SOL)
- **Win Rate**: 0% (early testing phase)
- **Total P&L**: -$1.33 (mostly from initial bug)

## Future Improvements

- [ ] Better position sizing algorithm
- [ ] More sophisticated entry signals
- [ ] Dynamic stop loss based on volatility
- [ ] Multiple position management
- [ ] Web dashboard for monitoring
- [ ] Backtesting framework
- [ ] Alert system for errors
