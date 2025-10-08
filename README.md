# Pacifica Trading Bot

Production-grade perpetual futures trading system for Pacifica (Solana) and Lighter (zkSync) DEXs.

## Current Status
- ✅ **Pacifica Bot**: Orderbook imbalance strategy (LIVE)
- ✅ **Lighter Bot**: VWAP mean reversion strategy (LIVE)
- ✅ **Health Monitoring**: `python3 monitor.py`

## Quick Start

```bash
# Check bot health
python3 monitor.py

# View live logs
tail -f logs/pacifica.log
tail -f logs/lighter_vwap.log

# Check positions
python3 -c "from trade_tracker import tracker; tracker.print_stats()"
```

## Architecture

```
pacifica-trading-bot/
├── bots/                    # Active bot executables
│   ├── live_pacifica.py    # Pacifica orderbook bot
│   └── vwap_lighter_bot.py # Lighter VWAP bot
├── strategies/              # Strategy implementations
│   ├── long_short.py       # Orderbook imbalance
│   └── vwap_strategy.py    # VWAP mean reversion
├── dexes/                   # DEX SDKs
│   ├── pacifica/
│   └── lighter/
├── logs/                    # All logs (gitignored)
├── config.py               # Global configuration
├── risk_manager.py         # Risk management
├── trade_tracker.py        # P&L tracking
└── monitor.py              # Health monitoring
```

## Current Strategies

### Pacifica - Orderbook Imbalance
- **Entry**: Weighted bid/ask depth ratio (>1.3 long, <0.7 short)
- **Exit**: Ladder TP (2%, 4%, 6%) OR 1% stop loss
- **Position**: $30-40 per trade
- **Filters**: <0.1% spread, min 5 orders/side

### Lighter - VWAP Mean Reversion
- **Entry**: Price >3% from VWAP with orderbook confluence
- **Exit**: 3% TP OR 1% SL (3:1 risk/reward)
- **Position**: ~$20 per trade
- **Advantage**: Zero trading fees

## Development

See [CONVENTIONS.md](CONVENTIONS.md) for coding standards.

## Environment

```bash
# Required
SOLANA_PRIVATE_KEY=<base58_key>
LIGHTER_API_KEY=<api_key>
LIGHTER_API_SECRET=<api_secret>
```

## Monitoring

Automated health checks run via `monitor.py`:
- Process alive
- Logs being written
- No silent failures

Run manually: `python3 monitor.py`
