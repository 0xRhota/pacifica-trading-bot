# Funding Rate Sources - Quick Reference

**Quick lookup table for funding rate data sources**

## 🏆 Top Recommendations (Ranked by Quality)

### 1. Binance Futures (Best Overall)
- **Endpoint**: `https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT`
- **Auth**: None (public)
- **Free**: ✅ Yes
- **Real-time**: ✅ Yes (8h cycles)
- **Use**: Production-grade, industry standard, years of history

```bash
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT"
```

### 2. Drift Protocol (Best for Solana-native)
- **Endpoint**: `wss://dlob.drift.trade/markets` (WebSocket)
- **Auth**: None (public)
- **Free**: ✅ Yes
- **Real-time**: ✅ Yes (hourly updates)
- **Use**: Solana-native perps, <100ms latency

### 3. Bybit (Good Alternative)
- **Endpoint**: `https://api.bybit.com/v5/market/funding/history?category=linear&symbol=SOLUSDT&limit=1`
- **Auth**: None (public)
- **Free**: ✅ Yes
- **Real-time**: ✅ Yes (8h cycles)
- **Use**: Backup to Binance, good latency

### 4. OKX (Good Alternative)
- **Endpoint**: `https://www.okx.com/api/v5/public/funding-rate?instId=SOL-USDT-SWAP`
- **Auth**: None (public)
- **Free**: ✅ Yes
- **Real-time**: ✅ Yes (8h cycles)
- **Use**: Third option for comparison

---

## By Use Case

### I want to avoid high funding rates (protect profitability)
**Use**: Binance + Bybit + OKX
- Poll all 3 every 30 seconds
- Take minimum rate (best deal)
- Avoid if any >0.05% per 8h

### I only trade Solana-native perps (Drift/Mango)
**Use**: Drift Protocol DLOB
- Subscribe to WebSocket for real-time
- Most accurate for on-chain positions
- Fallback: Solana RPC direct query

### I want to see which exchange has best rates
**Use**: Coinglass API (aggregator)
- Shows all exchanges at once
- Good for analysis (1h delay)
- Limited free tier (100 req/day)

---

## Quick Test Commands

```bash
# Binance
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT"

# Bybit
curl "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=SOLUSDT&limit=1"

# OKX
curl "https://www.okx.com/api/v5/public/funding-rate?instId=SOL-USDT-SWAP"

# Drift Protocol (requires WebSocket client)
# wss://dlob.drift.trade

# Coinglass (needs API key for high volume)
curl "https://api.coinglass.com/api/v2/futures/fundRate?symbol=SOL"
```

---

## Response Format Comparison

### Binance
```json
{
  "symbol": "SOLUSDT",
  "fundingRate": "0.00016840",
  "fundingTime": 1699999999000
}
```

### Bybit
```json
{
  "symbol": "SOLUSDT",
  "fundingRate": "0.00008",
  "fundingRateTimestamp": "1699999999000"
}
```

### OKX
```json
{
  "instId": "SOL-USDT-SWAP",
  "fundingRate": "0.00010",
  "nextFundingRate": "0.00008",
  "nextFundingTime": "1700000000000"
}
```

---

## Integration Checklist

- [ ] Decide on primary source (Binance recommended)
- [ ] Decide on fallback (Bybit recommended)
- [ ] Create wrapper class for unified interface
- [ ] Add to position tracking logic
- [ ] Test for 24 hours with logging
- [ ] Document API response times
- [ ] Set rate limits (polling frequency)

---

## Action Items

1. **This hour**: Test Binance endpoint with curl
2. **This hour**: Confirm Pacifica doesn't have native funding rate endpoint
3. **Today**: Create Python client for Binance funding rates
4. **This week**: Integrate into position management
5. **Next week**: Add to strategy decision logic

---

## ⚠️ Important Notes

- **Funding rates change every 8 hours** (Binance/Bybit/OKX)
- **Drift rates change hourly** (Solana-native)
- **Rates are exchange-specific** - SOL might be +0.05% on Binance, +0.02% on Bybit
- **Always compare rates before opening positions**
- **High funding rates kill profitability** - avoid if >0.1% per cycle
- **Funding flows FROM longs TO shorts** when rate is positive

---

## Data Age by Source

| Source | Update Frequency | Acceptable Age |
|--------|------------------|-----------------|
| Binance | Every 8 hours | 30 seconds |
| Bybit | Every 8 hours | 30 seconds |
| OKX | Every 8 hours | 30 seconds |
| Drift | Every hour | 5 minutes |
| Coinglass | Aggregated | 1 hour |

