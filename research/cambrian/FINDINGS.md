# Cambrian API Research Findings

## API Discovery

### Base URL
✅ **Confirmed**: `https://opabinia.cambrian.network` (NOT .org!)

### Authentication
✅ **Working**: Using `X-API-Key` header (capital X, capital K)

```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/tokens" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn" \
  -H "Content-Type: application/json"
```

**API Key**: `doug.ZbEScx8M4zlf7kDn` ✅ ACTIVE

## Available Endpoints (from Knowledge Base)

### Token Data
- `/api/v1/solana/tokens` - List all tokens
- `/api/v1/solana/tokens/security` - Token security metrics
- `/api/v1/solana/tokens/holders_over_time` - Holder count history
- `/api/v1/solana/tokens/holder_distribution_over_time` - Holder distribution

### Market Data
- `/api/v1/solana/ohlcv/base-quote` - OHLCV price data
- `/api/v1/solana/trending_tokens` - Trending tokens
- `/api/v1/solana/wallet-balance-history` - Wallet token balances

### Trading Intelligence
- `/api/v1/solana/traders/leaderboard` - Top traders
- `/api/v1/solana/trade-statistics` - Trade stats

## Perp Risk Engine
**Status**: NOT YET FOUND in knowledge base

The Cypher queries for perp-related endpoints returned empty results. This suggests:
1. Perp endpoints may not be ingested into knowledge base yet
2. May need to ingest perp documentation specifically
3. May be under different naming/path structure

## Deep42 Off-Chain Data
**Status**: NOT YET FOUND in knowledge base

No results for Deep42, off-chain, or signal-related endpoints.

## Focus Tokens
Target tokens for perps trading:
- XPL
- PENGU
- SOL (Solana)
- BTC (Bitcoin)
- ETH (Ethereum)
- HYPE
- ASTER

## Tested & Working Endpoints

### ✅ Trade Statistics
**Endpoint**: `/api/v1/solana/trade-statistics`
**Usefulness**: HIGH - provides buy/sell pressure signals

**Example SOL Data (24h)**:
- Buy Count: 2.6M transactions
- Sell Count: 7.8M transactions
- Total Volume: $5.86B USD
- Buy/Sell Ratio: 0.19 (BEARISH signal)

**Trading Signal**: Ratio < 0.9 = Bearish, > 1.1 = Bullish

### ✅ OHLCV Data
**Endpoint**: `/api/v1/solana/ohlcv/base-quote`
**Usefulness**: HIGH - price action and volume

**Available Intervals**: 1m, 5m, 15m, 1h, 4h, 1d
**Data Includes**:
- OHLC prices
- Volume (USD and tokens)
- Trade count
- Pool count
- Provider count

### ✅ Trending Tokens
**Endpoint**: `/api/v1/solana/trending_tokens`
**Usefulness**: MEDIUM - discover momentum

**Order By**:
- `price_change_24h` - biggest gainers/losers
- `volume_24h` - most traded
- `current_price` - by price

### ✅ Trader Leaderboard
**Endpoint**: `/api/v1/solana/traders/leaderboard`
**Usefulness**: MEDIUM - smart money tracking

**Shows**: Top traders by PnL and trade stats

## Perps Trading Signals

### Implemented in `cambrian_client.py`:

1. **Momentum Signal** (Working)
   - Uses buy/sell ratio from trade statistics
   - Signals: BULLISH (>1.1), BEARISH (<0.9), NEUTRAL
   - Current SOL: BEARISH (0.19 ratio)

2. **Volume Analysis** (Ready to implement)
   - 24h volume trends
   - Compare to historical average
   - High volume = strong signal confirmation

3. **Price Action** (OHLCV available)
   - Support/resistance levels
   - Trend detection
   - Volatility measurement

## Action Items

1. ✅ **API Authentication** - COMPLETE
2. ✅ **Basic Trading Signals** - COMPLETE (momentum via buy/sell ratio)
3. **Find Token Addresses** - Need addresses for: BTC, ETH, PENGU, XPL, HYPE, ASTER
4. **Advanced Signals**:
   - Combine volume + price action
   - Add OHLCV trend analysis
   - Integrate trader leaderboard data
5. **Integrate with Pacifica Bot**:
   - Add Cambrian signals to entry decision
   - Use buy/sell pressure to filter positions
   - Adjust position sizing based on momentum

## Notes
- Cambrian docs site is a React SPA (can't curl directly for examples)
- MCP ClickHouse tool requires SSH tunnel setup (not configured)
- Knowledge base has general token/market endpoints but missing perp-specific ones
