# Cambrian API Research

## Overview
Research into Cambrian API for perps trading signals on major tokens.

## Focus Tokens
- XPL
- PENGU
- SOL (Solana)
- BTC (Bitcoin)
- ETH (Ethereum)
- HYPE
- ASTER

## API Endpoints of Interest

### Perp Risk Engine
- **Endpoint**: `/v1/perp/risk-engine`
- **Purpose**: Risk metrics for perpetual trading
- **Documentation**: https://docs.cambrian.org/api/v1/perp-risk-engine

### Deep42 Off-Chain Data
- **Purpose**: Social sentiment and off-chain indicators
- **Focus**: Major tokens only (filter out shitcoins)

## Authentication
API Key stored in `.env` file (gitignored)

## Research Status
- [x] Created research folder structure
- [x] Stored API credentials
- [x] Fixed API authentication (X-API-Key header, cambrian.network domain)
- [x] Map available endpoints (trade stats, OHLCV, trending, leaderboard)
- [x] Built Python client (`cambrian_client.py`)
- [x] Implemented basic momentum signal (buy/sell ratio)
- [x] Tested with live SOL data
- [ ] Find token addresses for BTC, ETH, PENGU, XPL, HYPE, ASTER
- [ ] Integrate signals into Pacifica bot
- [ ] Backtest signal performance

## Current Signal Performance

**SOL Example (Current)**:
- Buy/Sell Ratio: 0.19 (BEARISH)
- 24h Volume: $5.86B
- Buy Transactions: 2.6M
- Sell Transactions: 7.8M
- **Signal**: BEARISH - avoid longs

## Files Created

1. **cambrian_client.py** - Main API client with trading signals
2. **test_api.py** - API endpoint explorer
3. **FINDINGS.md** - Complete research documentation
4. **INTEGRATION_PLAN.md** - Step-by-step integration guide
5. **.env** - API credentials (gitignored)

## Next Steps
1. Explore API documentation
2. Test endpoints with focus tokens
3. Identify actionable trading signals
4. Create integration plan for Pacifica bot
