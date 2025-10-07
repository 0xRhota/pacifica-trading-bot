# Pacifica Trading Bot

A live trading bot for Pacifica.fi (Solana perpetual derivatives exchange) designed for organic, profitable trading. This bot places **real orders with real money** and is optimized for conservative position sizing and risk management.

⚠️ **This bot trades with REAL MONEY on Pacifica.fi mainnet**

## Current Status

- ✅ **LIVE TRADING** - Bot is actively placing real orders
- 🎯 Position Size: $10-$15 per trade
- 📈 Strategy: Longs only (bull market mode)
- ⏰ Trade Frequency: Every 15 minutes
- 🛡️ Risk Controls: 0.3% stop loss, 5% take profit

## Features

### Trading Strategy
- **Longs Only Mode**: Only opens long positions (bull market optimized)
- **Small Position Sizing**: $10-$15 per trade for conservative risk management
- **Automatic Risk Management**:
  - Stop loss at -0.3%
  - Take profit at +0.2%
  - Max hold time: 30 minutes
- **Organic Trading Pattern**:
  - Positions every 15 minutes
  - Position monitoring every 45 seconds
  - Random position sizing within limits

### Trade Tracking
- **Persistent Logging**: All trades saved to `trades.json`
- **Analytics**: Win rate, P&L, fees, best/worst trades
- **Statistics Dashboard**: View performance with `view_trades.py`

### Security
- **Wallet Signatures**: Ed25519 cryptographic signing via Solana wallet
- **Private Key Protection**: Stored in `.env` (gitignored)
- **Safety Checks**: Multiple layers of position size validation

## Quick Start

### 1. Install Dependencies
```bash
pip install aiohttp python-dotenv solders base58
```

### 2. Set Up Environment
Create a `.env` file in the project root with your Solana wallet private key.

⚠️ **NEVER commit the `.env` file to git!**

### 3. Configure Bot
Edit `config.py` to adjust trading parameters:
```python
MIN_POSITION_SIZE_USD = 10.0   # Minimum $10 (Pacifica requirement)
MAX_POSITION_SIZE_USD = 15.0   # Maximum $15 (conservative)
MIN_PROFIT_THRESHOLD = 0.05    # Take profit at +5%
MAX_LOSS_THRESHOLD = 0.003     # Stop loss at -0.3%
MAX_LEVERAGE = 5.0             # Maximum 5x leverage
```

### 4. Test Single Order (Optional)
```bash
python3 scripts/place_order_now.py
```
This places one test order to verify everything works.

### 5. Start Live Trading
```bash
python3 live_bot.py
```

Or run in background:
```bash
nohup python3 live_bot.py > live_bot_output.log 2>&1 &
```

## Monitoring

### View Live Activity
```bash
tail -f live_bot_output.log
```

### View Trading Statistics
```bash
python3 scripts/view_trades.py
```

Output example:
```
============================================================
TRADING STATISTICS
============================================================
Total Trades:      3
Winning Trades:    1
Losing Trades:     2
Win Rate:          33.33%
Total P&L:         $-1.33
Average P&L:       $-0.44
Total Fees:        $1.28
============================================================
```

### Check Bot Status
```bash
ps aux | grep "python.*live_bot"
```

### Check Account Balance
The bot logs balance info on startup and periodically.

## Configuration

### Trading Parameters (`config.py`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| MIN_POSITION_SIZE_USD | 10.0 | Minimum position size (Pacifica requirement) |
| MAX_POSITION_SIZE_USD | 15.0 | Maximum position size (risk limit) |
| MIN_PROFIT_THRESHOLD | 0.05 | Take profit at +5% |
| MAX_LOSS_THRESHOLD | 0.003 | Stop loss at -0.3% |
| MAX_LEVERAGE | 5.0 | Maximum leverage allowed |
| LOT_SIZE | 0.01 | Minimum order size increment |
| CHECK_FREQUENCY_SECONDS | 45 | Position check interval |
| TRADE_FREQUENCY_SECONDS | 900 | Time between new positions (15 min) |
| MAX_POSITION_HOLD_TIME | 1800 | Maximum hold time (30 min) |
| LONGS_ONLY | True | Only open long positions |

### Trading Symbols
- SOL - Solana
- PENGU - Pudgy Penguins
- BTC - Bitcoin
- XPL - XPL token
- ASTER - Aster token

## Architecture

### Core Files

| File | Purpose |
|------|---------|
| `live_bot.py` | Main trading bot - handles all live trading |
| `pacifica_sdk.py` | SDK wrapper for order placement with wallet signing |
| `pacifica_bot.py` | API client for market data and account info |
| `trade_tracker.py` | Trade logging and analytics engine |
| `strategies.py` | Trading strategy logic |
| `risk_manager.py` | Risk management and position validation |
| `config.py` | Configuration settings |

### Helper Scripts

| Script | Purpose |
|--------|---------|
| `place_order_now.py` | Test script to place single order |
| `view_trades.py` | Display trading statistics |

### Data Files

| File | Purpose | Gitignored? |
|------|---------|-------------|
| `.env` | Private keys and secrets | ✅ Yes |
| `trades.json` | Trade history and logs | ✅ Yes |
| `*.log` | Log files | ✅ Yes |

## API Details

### Pacifica API
```
Base URL: https://api.pacifica.fi/api/v1

GET  /book?symbol={symbol}      # Orderbook data
GET  /price?symbol={symbol}     # Current price
GET  /account?address={addr}    # Account information
POST /order                     # Place order (requires signature)
```

### Order Placement
Orders require Solana wallet signature:
```python
# Signature structure
signature_header = {
    "timestamp": int(time.time() * 1000),
    "expiry_window": 5000,
    "type": "create_market_order"
}

signature_payload = {
    "symbol": "SOL",
    "amount": "0.05",
    "side": "bid",  # or "ask" for shorts
    "slippage_percent": "1.0"
}
```

## Risk Management

### Position Sizing
- All positions: $10-$15
- Rounded to 0.01 lot size increments
- Safety check: rejects orders >$30

### Stop Loss / Take Profit
- **Stop Loss**: Automatic close at -0.3% loss
- **Take Profit**: Automatic close at +5% profit
- **Time Limit**: Forced close after 30 minutes

### Leverage Control
- Maximum 5x leverage
- Bot won't open new positions if at max leverage
- Current leverage monitored on each cycle

### Error Handling
- API connection errors: retry on next cycle
- Order failures: logged but continue trading
- Position tracking: synced with Pacifica API

## Trade Tracking

All trades are logged to `trades.json` with entry/exit prices, P&L, fees, and exit reasons.

## Safety Features

### Code Safety
- ✅ Position size validation before every order
- ✅ Safety check prevents orders >2x max size
- ✅ Leverage limits enforced
- ✅ Stop losses on all positions

### Operational Safety
- ✅ Private keys in `.env` (gitignored)
- ✅ Ed25519 cryptographic signatures
- ✅ API errors handled gracefully
- ✅ Comprehensive logging

### Risk Limits
- ✅ Max position: $15 (small account protection)
- ✅ Max leverage: 5x
- ✅ Max hold time: 30 minutes
- ✅ Stop loss: -0.3%

## Troubleshooting

### Bot Won't Start
```bash
# Check if .env exists
ls -la .env

# Verify Python version (requires 3.9+)
python3 --version

# Check dependencies
pip list | grep -E "aiohttp|solders|base58"
```

### Orders Failing
Common issues:
1. **Not Multiple of Lot Size**: Orders must be 0.01 increments
2. **Below Minimum**: Orders must be ≥$10
3. **API Connection**: Check network connection
4. **Insufficient Balance**: Check account balance

### Bot Stopped
```bash
# Check if running
ps aux | grep "python.*live_bot"

# View recent logs
tail -50 live_bot_output.log

# Restart
python3 live_bot.py
```

## Development

### Adding New Features
1. Read `CLAUDE.md` for project context
2. Check `PROGRESS.md` for development history
3. Test changes with `place_order_now.py` first
4. Update documentation
5. Commit with descriptive message

### Testing
```bash
# Test single order
python3 scripts/place_order_now.py

# View current positions
python3 -c "from pacifica_bot import *; import asyncio; asyncio.run(check_positions())"

# Check trade stats
python3 scripts/view_trades.py
```

## Documentation

- **README.md**: This file - user-facing documentation
- **docs/CLAUDE.md**: Comprehensive guide for AI development
- **docs/PROGRESS.md**: Complete development history and lessons learned
- **docs/SETUP.md**: Original setup instructions

## Repository

- **GitHub**: github.com/0xRhota/pacifica-trading-bot
- **Branch**: main

## Legal Disclaimer

⚠️ **Important**: This bot trades with real money on live markets.

- **Risk of Loss**: Trading cryptocurrencies involves substantial risk of loss
- **No Guarantees**: Past performance does not guarantee future results
- **Your Responsibility**: You are solely responsible for your trading decisions
- **Compliance**: Ensure compliance with all applicable laws and regulations
- **Platform Terms**: Use must comply with Pacifica.fi terms of service

## License

This project is for educational purposes. Use at your own risk.

---

**Status**: 🟢 LIVE TRADING
**Last Updated**: 2025-10-06
**Bot Version**: 1.0.0
