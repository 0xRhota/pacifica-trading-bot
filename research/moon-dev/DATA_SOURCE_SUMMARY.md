# Current vs Cambrian Data Source - Summary

**Current Status**: RBI agent uses **Pacifica API** for historical OHLCV data  
**Analysis Date**: 2025-11-01

---

## Current Data Source: Pacifica API

**What RBI Agent Uses**:
- Endpoint: `/api/v1/kline` 
- Data: OHLCV candles (open, high, low, close, volume)
- Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d
- **Limit**: Max 1000 candles per request
- **Problem**: 90 days × 96 candles/day = 8,640 candles needed → Requires **9+ API calls**

**Code Location**: `rbi_agent/rbi_agent.py` (lines 62-116)

---

## Cambrian API - Better Option for Backtesting

### `/api/v1/solana/ohlcv/token` - Token OHLCV (All Venues) ⭐ RECOMMENDED

**Key Advantages**:
- ✅ **Time range queries** - Direct `after_time`/`before_time` (no limit calculations)
- ✅ **Single request** - Fetch entire 90 days in one call
- ✅ **Multi-venue aggregation** - More accurate (aggregated across all Solana DEXs)
- ✅ **USD normalized** - Prices already in USD
- ✅ **Historical coverage** - Full current year available

**Parameters**:
```python
{
    "token_address": "So11111111111111111111111111111111111111112",  # SOL
    "after_time": 1735689600,  # Unix timestamp (seconds)
    "before_time": 1735776000,
    "interval": "15m"  # 1m, 5m, 15m, 1h, 4h, 1d
}
```

**Returns**:
- `openPrice`, `highPrice`, `lowPrice`, `closePrice` (USD)
- `volume` (USD), `volumeToken` (native units)
- `unixTime`, `interval`, `tokenAddress`

**API Reference**: [Cambrian OpenAPI Spec](https://opabinia.cambrian.org/openapi.json)

---

## Comparison

| Feature | Pacifica (Current) | Cambrian (Better) |
|---------|-------------------|-------------------|
| **90-Day Data** | 9+ API calls needed | ✅ Single request |
| **Time Range** | ❌ Limit-based | ✅ Direct time range |
| **Multi-Venue** | ❌ Pacifica only | ✅ All DEXs aggregated |
| **Request Limit** | ❌ 1000 candles max | ✅ No limit |
| **USD Prices** | ❌ Native prices | ✅ USD normalized |
| **Historical** | ⚠️ Limited | ✅ Full year |

---

## Implementation Requirements

### 1. Token Address Mapping
**Status**: Partial mapping exists at `scripts/research/solana_token_mapping.py`

**Current Coverage**:
- ✅ SOL: `So11111111111111111111111111111111111111112`
- ❌ Need to map: ETH, BTC, PUMP, and others

**Solution**: Use Cambrian's `/solana/token-details` to lookup addresses by symbol

### 2. Create Cambrian Data Fetcher
New class: `CambrianDataFetcher` (similar to `PacificaDataFetcher`)

### 3. Update StrategyBacktester
Modify `fetch_historical_data()` to use Cambrian by default

---

## Recommendation

**Migrate RBI agent to Cambrian for backtesting**:
- ✅ More efficient (single request vs 9+)
- ✅ More accurate (multi-venue data)
- ✅ Better historical coverage
- ✅ Already have API key (`doug.ZbEScx8M4zlf7kDn`)

**Keep Pacifica for live trading** (real-time data, funding rates)

---

**Full Analysis**: See `rbi_agent/DATA_SOURCE_ANALYSIS.md`  
**Current Backtest**: Running with Pacifica (will complete in ~20-30 min)  
**Next Step**: Implement Cambrian fetcher for future backtests


