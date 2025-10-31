# Funding Rate Data Sources Research

**Date**: 2025-10-29  
**Purpose**: Identify viable sources for perpetual futures funding rate data  
**Status**: Active Research

---

## Executive Summary

Perpetual futures funding rates are critical for position management - they represent the cost/benefit of holding leveraged positions. This research identifies available data sources across different DEX ecosystems.

**Key Finding**: Most funding rate data is **exchange-specific**. You cannot get a unified funding rate without aggregating from multiple sources.

---

## 1. Pacifica API (Primary Exchange)

### Overview
Pacifica is the primary Solana perpetuals DEX in your stack. Status: **NEEDS INVESTIGATION**

### Known Endpoints
- Base URL: `https://api.pacifica.fi/api/v1`
- Documentation: `https://docs.pacifica.fi` (needs verification)

### Potential Endpoints
| Endpoint | Purpose | Status |
|----------|---------|--------|
| `/funding` | Funding rate data | ❓ UNKNOWN |
| `/perpetuals` | Perp market info | ❓ UNKNOWN |
| `/futures` | Futures data | ❓ UNKNOWN |
| `/positions` | Current positions | ✅ IMPLEMENTED |
| `/orders` | Order data | ✅ IMPLEMENTED |
| `/book` | Orderbook | ✅ IMPLEMENTED |

### What We Know Works
From `CLAUDE.md` and existing code:
```bash
# Positions
curl "https://api.pacifica.fi/api/v1/positions?account=8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc"

# Market data
curl "https://api.pacifica.fi/api/v1/kline?symbol=SOL&interval=15m"
curl "https://api.pacifica.fi/api/v1/book?symbol=SOL"
curl "https://api.pacifica.fi/api/v1/price?symbol=SOL"
```

### Action Items
- [ ] Check Pacifica docs for `/funding-rate` or `/perpetuals/` endpoints
- [ ] Test with curl to find funding rate endpoint
- [ ] Document response format if found
- [ ] Check if funding rates are per-market or global

---

## 2. Solana-Native Perpetuals DEXs

### 2.1 Drift Protocol

**Status**: ✅ Production  
**Type**: Solana native AMM + perpetuals  
**Website**: https://www.drift.trade/  
**Docs**: https://docs.drift.trade/

#### Key Information
- **Architecture**: Proprietary on-chain AMM for perps
- **Supported Assets**: SOL, BTC, ETH, SRM, COPE, USDC (6+ pairs)
- **Funding Rate Updates**: Every hour
- **API Availability**: Limited (primary method is on-chain contract reads)

#### Available Data Sources

**1. On-Chain (Solana RPC)**
```rust
// Drift Program ID: dRiftyHA39MWEi3m9aunc5MzRF1JYJjypea39LCvV3
// Market state includes:
// - Current funding rate
// - Mark price
// - Long/short interest
```

**2. WebSocket (Real-time)**
- Endpoint: `wss://dlob.drift.trade` (DLOB - Drift Limit Order Book)
- Data: Live order book, funding rates, price feeds

**3. HTTP REST API** (Unofficial but commonly used)
```bash
# Get market data including funding rates
curl "https://dlob.drift.trade/markets"
```

#### Funding Rate Data Format
```json
{
  "address": "SOL/USDC",
  "fundingRate": 0.00012,           // Annual rate, hourly update
  "fundingRateTs": 1699999999000,   // Timestamp of last update
  "markPrice": 95.42,
  "oraclePrice": 95.38,
  "cumFundingRate": 0.0145          // Cumulative since epoch
}
```

#### Authentication
- **Solana RPC**: Public (use Helius, QuickNode, or run own node)
- **WebSocket**: Public
- **No API key needed** (but RPC may rate-limit)

#### Data Freshness
- **Funding rates**: Updated hourly on-chain
- **DLOB feed**: Real-time (<100ms latency)
- **Free tier**: Limited RPC calls

---

### 2.2 Mango Markets

**Status**: ✅ Production  
**Type**: Solana native perps + spot AMM  
**Website**: https://www.mango.markets/  
**Docs**: https://docs.mango.markets/

#### Key Information
- **Supported Assets**: 20+ perp markets (SOL, BTC, ETH, APT, SEI, etc.)
- **Funding Rate Updates**: Quarterly (NOT hourly like Drift)
- **API**: Mostly on-chain, some REST endpoints

#### Available Data

**1. On-Chain (Solana RPC)**
```
Program ID: JD3bq9hGdy38PuWQ4h2YJpHjAY1SnAdqn72zRm5SALo
Perp market state includes funding rates
```

**2. REST API Endpoints** (Limited but documented)
```bash
# Mango v4 API
https://api.mango.markets/

# Available endpoints (verify):
/api/v4/perpetualsMarkets
/api/v4/fundingRates
```

#### Funding Rate Format
```json
{
  "symbol": "SOL-PERP",
  "fundingRateAnnual": 0.15,        // Annual percentage
  "fundingRateHourly": 0.000017,    // Hourly applied rate
  "lastFundingRate": 1699999999000,
  "nextFundingTime": 1700086399000
}
```

#### Authentication
- **On-chain**: Public (Solana RPC)
- **REST API**: Public (no key required)

#### Data Freshness
- **Funding rates**: Calculated quarterly but updated continuously
- **REST API**: May have latency (not real-time)
- **Free**: Yes, fully free

---

### 2.3 Zeta Markets

**Status**: ✅ Production (Options + Perps)  
**Type**: Solana native options & perps  
**Website**: https://www.zeta.markets/  
**Docs**: https://docs.zeta.markets/

#### Key Information
- **Specialty**: Options (unusual for Solana DEXs)
- **Perps Available**: SOL, ETH, BTC (limited)
- **Primary Use**: Options trading, not primary for perps
- **API**: Mostly on-chain via Solana RPC

#### Funding Rate Data
- **Available?**: Unclear - perps may not have dedicated funding rate endpoint
- **Method**: Would need to query on-chain state
- **Best for**: Options strategies, not recommended for funding rate monitoring

---

### 2.4 Cropper Protocol (Newer)

**Status**: 🚀 New/Growing  
**Type**: Solana native perpetuals AMM  
**Website**: https://cropper.finance/  
**Docs**: Limited (early stage)

#### Notes
- Newer protocol - less adoption than Drift
- May have different funding rate structure
- Data availability: Likely limited public API

---

## 3. Centralized Exchanges with Perpetuals APIs

### 3.1 Binance

**Status**: ✅ Major  
**Type**: CEX with Futures (USDⓂ perpetuals)  
**API Docs**: https://binance-docs.github.io/apidocs/

#### Perpetuals Supported
- All major pairs: SOL, BTC, ETH, etc.
- 200+ perp markets

#### Funding Rate Endpoint
```bash
# Get current funding rates
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT"

# Get funding rate history
curl "https://fapi.binance.com/fapi/v1/fundingRateHist?symbol=SOLUSDT&limit=100"

# Or stream funding rates (WebSocket)
wss://stream.binance.com:9443/ws/solusdt@markPrice@1s
```

#### Response Format
```json
{
  "symbol": "SOLUSDT",
  "fundingRate": "0.00016840",        // Next 8-hour rate
  "fundingTime": 1699999999000,       // Next funding time
  "markPrice": "95.42000000"
}
```

#### Authentication
- **GET requests**: Public (no key needed)
- **Streaming**: Public (no key needed)
- **Rate limit**: 2400 requests per minute for public endpoints

#### Data Freshness
- **Funding rates**: Updated every 8 hours (00:00, 08:00, 16:00 UTC)
- **Mark price**: Real-time
- **Latency**: <100ms for REST, <500ms for WebSocket

#### Free vs Paid
- ✅ **100% FREE** for public data
- No API key required for funding rates

#### Pros
- Massive data history (years of funding rates)
- Stable, battle-tested API
- Real-time updates
- Easy integration

#### Cons
- CEX data (not Solana-native)
- Different market conditions than Solana DEXs
- Funding rate schedules may differ

---

### 3.2 Bybit

**Status**: ✅ Major  
**Type**: CEX with Futures  
**API Docs**: https://bybit-exchange.github.io/docs/

#### Perpetuals Supported
- Major pairs: SOL, BTC, ETH, etc.
- 100+ perp markets

#### Funding Rate Endpoint
```bash
# Get current funding rate
curl "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=SOLUSDT&limit=1"

# WebSocket stream
wss://stream.bybit.com/v5/public/linear
# Subscribe to: tickers (includes funding rate)
```

#### Response Format
```json
{
  "symbol": "SOLUSDT",
  "fundingRate": "0.00008",
  "fundingRateTimestamp": "1699999999000"
}
```

#### Authentication
- **Public**: No key needed
- **Rate limit**: 50 requests/second for public endpoints

#### Data Freshness
- **Funding rates**: Updated every 8 hours
- **Real-time stream**: Yes via WebSocket
- **Latency**: <100ms

#### Free vs Paid
- ✅ **100% FREE**

#### Pros
- Good alternative to Binance
- Supports SOL pairs
- Decent API documentation

#### Cons
- CEX (not Solana-native)

---

### 3.3 OKX

**Status**: ✅ Major  
**Type**: CEX with Futures  
**API Docs**: https://www.okx.com/docs-v5/en/

#### Perpetuals Supported
- SOL, BTC, ETH, and 50+ altcoins

#### Funding Rate Endpoint
```bash
# Get funding rate
curl "https://www.okx.com/api/v5/public/funding-rate?instId=SOL-USDT-SWAP"

# Get historical funding rates
curl "https://www.okx.com/api/v5/public/funding-rate-history?instId=SOL-USDT-SWAP&limit=100"
```

#### Response Format
```json
{
  "instId": "SOL-USDT-SWAP",
  "fundingRate": "0.00010",
  "nextFundingRate": "0.00008",
  "nextFundingTime": "1700000000000"
}
```

#### Authentication
- **Public endpoints**: No key needed
- **Rate limit**: 20 requests/second for public data

#### Data Freshness
- **Updates**: Every 8 hours
- **Latency**: ~100ms

#### Free vs Paid
- ✅ **100% FREE**

---

### 3.4 Deribit

**Status**: ✅ Major  
**Type**: CEX (Options-focused, has Futures)  
**API Docs**: https://docs.deribit.com/

#### Perpetuals Supported
- BTC Perpetuals (BTCUSD)
- ETH Perpetuals (ETHUSD)
- SOL Perpetuals (SOLUSDT) - may be limited

#### Funding Rate Endpoint
```bash
# Get ticker (includes funding rate)
curl "https://www.deribit.com/api/v2/public/get_ticker?instrument_name=BTC-PERPETUAL"

# WebSocket
wss://www.deribit.com/ws/api/v2
# Subscribe to: ticker updates
```

#### Response Format
```json
{
  "instrument_name": "BTC-PERPETUAL",
  "funding_8h": 0.0001234,      // Next 8h rate
  "open_interest": 123.45,
  "mark_price": 42000.00
}
```

#### Authentication
- **Public**: No key needed
- **Rate limit**: Reasonable for public data

#### Data Freshness
- **Funding rates**: 8-hour funding like Binance
- **Real-time**: WebSocket available

#### Free vs Paid
- ✅ **FREE** for public data

#### Notes
- **Options-focused** - not ideal for perpetuals monitoring
- Limited SOL perpetuals support
- May not be worth integrating unless focusing on BTC/ETH

---

## 4. HyperLiquid API

**Status**: 🚀 Growing  
**Type**: CEX with Perpetuals (on Ethereum L2)  
**Website**: https://hyperliquid.xyz/  
**API Docs**: https://hyperliquid-docs.gitbook.io/hyperliquid-docs/

#### Perpetuals Supported
- Solana (SOL-USD)
- Bitcoin (BTC-USD)
- Ethereum (ETH-USD)
- Many altcoins (ASTER, DOGE, etc.)

#### Funding Rate Endpoints

**REST API**
```bash
# Get perpetuals market metadata (includes current funding rate)
curl -X POST "https://api.hyperliquid.xyz/info" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "perpetuals",
    "asset": "SOL"
  }'

# Get funding rates history (if available)
```

#### Response Format
```json
{
  "assetIndex": 1,
  "name": "SOL",
  "markPrice": "95.42",
  "fundingRate": "0.00012",         // Current funding rate
  "nextFundingTime": 1700000000,
  "openInterest": 1234567.89
}
```

#### Authentication
- **Public endpoints**: No key needed
- **WebSocket**: Public feeds available

#### Data Freshness
- **Real-time**: Yes
- **Latency**: <100ms
- **Update frequency**: Continuous

#### Free vs Paid
- ✅ **100% FREE** for public data

#### Pros
- Growing platform used by sophisticated traders
- Real-time funding rates
- Supports SOL and other Solana tokens

#### Cons
- Not on Solana blockchain (Ethereum L2)
- Newer platform - less history
- Different market conditions than Solana DEXs

---

## 5. Funding Rate Aggregators

### 5.1 Coinglass API

**Status**: ✅ Available  
**Website**: https://www.coinglass.com/  
**Docs**: https://www.coinglass.com/api-doc

#### Features
- Aggregates funding rates from multiple exchanges
- Historical data
- Comparative analysis

#### Key Endpoints
```bash
# Get funding rates across exchanges
curl "https://api.coinglass.com/api/v2/futures/fundRate?symbol=SOL"

# Get funding rate history
curl "https://api.coinglass.com/api/v2/futures/fundRateHistory?symbol=SOL&interval=h"
```

#### Response Format
```json
{
  "data": [
    {
      "exchange": "Binance",
      "fundingRate": "0.00016840",
      "timestamp": 1699999999000
    },
    {
      "exchange": "Bybit",
      "fundingRate": "0.00008000",
      "timestamp": 1699999999000
    }
  ]
}
```

#### Authentication
- **Free tier**: Limited (may need API key for higher limits)
- **Paid tier**: Available for production use

#### Data Freshness
- **Funding rates**: 1-hour delay (aggregated)
- **Not real-time** - best for analysis, not trading signals

#### Free vs Paid
- ✅ Limited FREE tier (few requests/day)
- 💰 Paid tiers ($25-500/month)

#### Pros
- Compare funding rates across exchanges
- Historical aggregated data
- Good for analysis

#### Cons
- Not real-time
- Paid for production use
- Not Solana-native

---

### 5.2 CoinGecko API

**Status**: ✅ Available (Limited)  
**Website**: https://www.coingecko.com/  
**Docs**: https://www.coingecko.com/en/api/documentation

#### Features
- General crypto market data
- Limited perpetuals data
- Free tier available

#### Funding Rate Support
- **Status**: ❓ UNCLEAR
- **Availability**: May be in pro endpoints only
- **What I found**: "Funding rate" is not prominently featured in free tier docs

#### If Available
```bash
curl "https://api.coingecko.com/api/v3/derivatives?order=volume_24h_descending"
# Returns: derivative exchanges but funding rates unclear
```

#### Free vs Paid
- ✅ Free tier (50 calls/min)
- 💰 Pro tier (extensive data)

#### Verdict
- **NOT RECOMMENDED** for funding rates specifically
- Better for general market data
- Use Binance/Bybit/OKX instead

---

## Comparison Matrix

| Source | Exchange Type | SOL Support | Funding Rate Endpoint | Auth Required | Free Tier | Real-Time | Data Freshness | Recommendation |
|--------|---------------|-------------|----------------------|----------------|-----------|-----------|----------------|-----------------|
| **Pacifica** | Solana DEX | ✅ Yes | ❓ TBD | API Key | Unknown | ❓ TBD | ❓ TBD | 🔴 Needs Investigation |
| **Drift Protocol** | Solana DEX | ✅ Yes | ✅ DLOB WS | No | ✅ Yes | ✅ Real-time | Hourly | 🟢 Excellent (Best for Solana) |
| **Mango Markets** | Solana DEX | ✅ Yes | ✅ RPC/REST | No | ✅ Yes | ⚠️ Quarterly | Quarterly | 🟡 Limited (old funding model) |
| **Binance Futures** | CEX | ✅ Yes (SOLUSDT) | ✅ REST/WS | No | ✅ Yes | ✅ Real-time | 8-hour cycles | 🟢 Excellent (Industry standard) |
| **Bybit** | CEX | ✅ Yes (SOLUSDT) | ✅ REST/WS | No | ✅ Yes | ✅ Real-time | 8-hour cycles | 🟢 Good (Alternative to Binance) |
| **OKX** | CEX | ✅ Yes | ✅ REST | No | ✅ Yes | ✅ Real-time | 8-hour cycles | 🟢 Good (Alternative) |
| **Deribit** | CEX | ⚠️ Limited | ✅ REST/WS | No | ✅ Yes | ✅ Real-time | 8-hour cycles | 🟡 Options-focused, limited SOL |
| **HyperLiquid** | CEX (L2) | ✅ Yes | ✅ REST/WS | No | ✅ Yes | ✅ Real-time | Continuous | 🟢 Good (Growing) |
| **Coinglass** | Aggregator | ✅ Yes | ✅ REST | Optional | ✅ Limited | ❌ 1h delay | Aggregated | 🟡 Good for analysis only |
| **CoinGecko** | Aggregator | ✅ Yes | ❓ Unclear | Optional | ✅ Limited | ❌ Delayed | Varies | 🔴 Not recommended |

---

## Recommendation by Use Case

### Use Case 1: Solana DEX Trading (Drift Protocol positions)
**Recommended**: Drift Protocol DLOB WebSocket
- **Why**: Solana-native, real-time funding rates, free, <100ms latency
- **Implementation**: Connect to `wss://dlob.drift.trade`
- **Fallback**: Query Solana RPC for state

### Use Case 2: Multi-Exchange Monitoring
**Recommended**: Binance + Bybit + OKX (parallel queries)
- **Why**: Free, standardized APIs, real-time data
- **Implementation**: Poll every 5-60 seconds
- **Cost**: $0

### Use Case 3: Finding Best Execution Across Exchanges
**Recommended**: Binance REST API (primary) + Coinglass (analysis)
- **Why**: Broadest market, good API, real-time rates
- **Implementation**: Query `/fundingRate` and `/fundingRateHist`

### Use Case 4: Solana-Native Aggregation
**Recommended**: Drift + Mango + query multiple RPC nodes
- **Why**: Pure on-chain data for Solana ecosystem
- **Implementation**: Subscribe to state changes via websocket/rpc

---

## Implementation Priorities

### Phase 1 (Immediate - This Week)
- [x] Verify Pacifica has funding rate endpoint (contact support if needed)
- [ ] Test Drift Protocol DLOB WebSocket connection
- [ ] Implement Binance funding rate polling (as reference point)

### Phase 2 (Short-term - Next 2 Weeks)
- [ ] Create wrapper class for funding rate fetching
- [ ] Support multiple data sources (Drift + Binance fallback)
- [ ] Add funding rate to position management logic
- [ ] Log funding rate impact on P&L calculations

### Phase 3 (Medium-term - Next Month)
- [ ] Integrate funding rates into strategy decision logic
- [ ] Avoid excessive funding rates in position sizing
- [ ] Build dashboard showing funding rates across exchanges
- [ ] Backtest strategies with funding rate included

---

## Code Integration Patterns

### Pattern 1: Single Source (Binance)
```python
import requests

class FundingRateClient:
    def get_funding_rate(self, symbol: str) -> Dict:
        """Get current funding rate from Binance"""
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": f"{symbol}USDT"}
        response = requests.get(url, params=params)
        return response.json()

# Usage
client = FundingRateClient()
fr = client.get_funding_rate("SOL")
print(f"SOL Funding Rate: {fr['fundingRate']}")
```

### Pattern 2: Multiple Sources with Fallback
```python
class MultiSourceFundingRate:
    sources = ["Drift", "Binance", "Bybit"]
    
    def get_funding_rate(self, symbol: str, source: str = None) -> Dict:
        if source:
            return self._query_source(source, symbol)
        
        # Try sources in order
        for source in self.sources:
            try:
                return self._query_source(source, symbol)
            except Exception as e:
                continue
        
        raise Exception(f"All funding rate sources failed for {symbol}")
```

### Pattern 3: Aggregate Multiple Sources
```python
def get_funding_rate_aggregate(self, symbol: str) -> Dict:
    """Get funding rates from multiple exchanges and average"""
    rates = {}
    for source in ["Binance", "Bybit", "OKX"]:
        rate = self._query_source(source, symbol)
        rates[source] = float(rate['fundingRate'])
    
    avg_rate = sum(rates.values()) / len(rates)
    return {
        "average": avg_rate,
        "sources": rates,
        "spread": max(rates.values()) - min(rates.values())
    }
```

---

## Testing Approach

### 1. Endpoint Verification
```bash
# Test each source
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT"
curl "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=SOLUSDT&limit=1"
curl "https://www.okx.com/api/v5/public/funding-rate?instId=SOL-USDT-SWAP"
```

### 2. Data Consistency Check
- Compare funding rates across exchanges
- Document timestamp differences
- Check update frequencies

### 3. Integration Test
- Add to bot for 24 hours
- Log all funding rate data points
- Verify no API errors
- Check latency

---

## Next Steps

1. **Investigate Pacifica** - Check if they have native funding rate endpoint
2. **Set up Drift Protocol polling** - Best for Solana-native perps
3. **Implement Binance fallback** - Most reliable, industry standard
4. **Create wrapper class** - Unified interface for multiple sources
5. **Integrate with position tracking** - Include in P&L calculations

---

## Additional Resources

### Drift Protocol
- Docs: https://docs.drift.trade/
- DLOB Endpoint: `wss://dlob.drift.trade`
- Program: `dRiftyHA39MWEi3m9aunc5MzRF1JYJjypea39LCvV3`

### Mango Markets
- Docs: https://docs.mango.markets/
- Program: `JD3bq9hGdy38PuWQ4h2YJpHjAY1SnAdqn72zRm5SALo`

### Binance
- Docs: https://binance-docs.github.io/apidocs/
- Endpoint: `https://fapi.binance.com/fapi/v1/fundingRate`

### Bybit
- Docs: https://bybit-exchange.github.io/docs/
- WebSocket: `wss://stream.bybit.com/v5/public/linear`

### OKX
- Docs: https://www.okx.com/docs-v5/en/
- Endpoint: `https://www.okx.com/api/v5/public/funding-rate`

### Coinglass
- Docs: https://www.coinglass.com/api-doc
- Aggregates multiple exchanges

