# RBI Agent Data Source Analysis

**Date**: 2025-11-01  
**Purpose**: Analyze current data sources and evaluate Cambrian API alternatives

---

## Current Data Source: Pacifica API

**What RBI Agent Uses**:
- `PacificaDataFetcher.fetch_market_data()` 
- Endpoint: `/api/v1/kline`
- Data: OHLCV candles (open, high, low, close, volume)
- Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d
- Limit: Max 1000 candles per request
- Timeframe: Last 90 days (limited by API)

**Limitations**:
- ❌ Max 1000 candles = ~10 days of 15m data (96 candles/day)
- ❌ Must make multiple requests for longer periods
- ❌ Only Pacifica-specific data (not aggregated across DEXs)
- ❌ No historical funding rates
- ❌ No liquidity/pool data

---

## Cambrian API Historical Endpoints

Based on [Cambrian OpenAPI spec](https://opabinia.cambrian.org/openapi.json), here are relevant historical data endpoints:

### 1. `/api/v1/solana/ohlcv/token` - Token OHLCV (All Venues) ⭐ BEST FOR BACKTESTING

**Purpose**: OHLCV aggregated across ALL trading venues (not just Pacifica)

**Parameters**:
- `token_address` (required): Solana token address (base58)
- `after_time` (required): Unix timestamp (seconds)
- `before_time` (required): Unix timestamp (seconds)
- `interval` (required): 1m, 5m, 15m, 1h, 4h, 1d

**Returns**:
- `openPrice`, `highPrice`, `lowPrice`, `closePrice` (USD)
- `volume` (USD), `volumeToken` (native units)
- `unixTime`, `interval`, `tokenAddress`

**Advantages**:
- ✅ **Multi-venue aggregation** - More accurate market data
- ✅ **Time range queries** - Can fetch exact date ranges
- ✅ **No per-request limit** - Uses time range, not limit
- ✅ **Historical data** - Available for current year
- ✅ **USD prices** - Already normalized

**Example**:
```bash
curl -X GET "https://opabinia.cambrian.org/api/v1/solana/ohlcv/token?token_address=So11111111111111111111111111111111111111112&after_time=1735689600&before_time=1735776000&interval=15m" \
  -H "X-API-KEY: doug.ZbEScx8M4zlf7kDn"
```

---

### 2. `/api/v1/solana/ohlcv/base-quote` - Base/Quote Pair OHLCV

**Purpose**: OHLCV for specific token pairs

**Parameters**:
- `base_address`, `quote_address` (required)
- `after_time`, `before_time` (required)
- `interval` (required): 1m, 5m, 15m, 1h, 4h, 1d

**Returns**:
- `openPrice`, `highPrice`, `lowPrice`, `closePrice` (quote units)
- `volume` (USD), `volumeBase` (base units)
- `tradeCount`, `poolCount`, `providerCount`

**Use Case**: Pair-specific analysis (e.g., SOL/USDC)

---

### 3. `/api/v1/solana/price-hour` - Historical Price Intervals

**Purpose**: Aggregated price at intervals (not full OHLCV)

**Parameters**:
- `token_address` (required)
- `interval` (required): 1H, 2H, 4H, 6H, 8H, 12H, 1D, 3D, 1W, 1M
- `limit`, `offset` (optional)

**Returns**:
- `priceUSD`: Average price for interval
- `datapoints`: Number of data points averaged
- `intervalStart`

**Use Case**: Lower granularity backtesting (daily/weekly)

---

### 4. `/api/v1/solana/price-volume/single` - Price + Volume Changes

**Purpose**: Current price/volume with percentage changes

**Parameters**:
- `token_address` (required)
- `timeframe` (required): 1h, 2h, 4h, 8h, 24h

**Returns**:
- `priceUSD`, `volumeUSD`
- `volumeChangePercent`, `priceChangePercent`

**Use Case**: Volume spike detection (not historical)

---

### 5. `/api/v1/solana/wallet-balance-history` - Wallet Balance History

**Purpose**: Historical wallet balance changes

**Parameters**:
- `wallet_address` (required)
- `token_address` (required)
- `after_time`, `before_time` (required)
- `limit`, `offset` (optional)

**Returns**:
- Balance changes with transaction details
- `preBalance`, `postBalance`, `changeAmount`

**Use Case**: Portfolio tracking, not trading backtesting

---

## Comparison: Pacifica vs Cambrian

| Feature | Pacifica API | Cambrian API |
|---------|-------------|--------------|
| **OHLCV Data** | ✅ Yes | ✅ Yes |
| **Multi-Venue** | ❌ Pacifica only | ✅ All venues aggregated |
| **Time Range** | ❌ Limit-based (1000 max) | ✅ Time range queries |
| **90-Day Coverage** | ⚠️ Requires multiple requests | ✅ Single request |
| **Historical Limits** | ⚠️ ~10 days per request | ✅ Current year |
| **USD Prices** | ❌ Native prices | ✅ USD normalized |
| **Funding Rates** | ✅ Current only | ❌ Not available |
| **Volume Data** | ✅ Yes | ✅ Yes (USD + token) |
| **API Key** | ✅ Required | ✅ Required |

---

## Recommendation: Migrate to Cambrian for Backtesting

### Why Cambrian is Better for Backtesting:

1. **Time Range Queries**
   - Pacifica: Must calculate `limit` based on days (e.g., 90 days × 96 = 8640 candles)
   - Cambrian: Direct `after_time`/`before_time` - fetch exactly what you need

2. **No Request Limits**
   - Pacifica: Max 1000 candles = ~10 days of 15m data
   - Cambrian: No limit - fetches entire time range in one request

3. **Multi-Venue Data**
   - Pacifica: Only Pacifica DEX data
   - Cambrian: Aggregated across all Solana DEXs (more accurate)

4. **Better Historical Coverage**
   - Pacifica: Limited by API
   - Cambrian: Full current year available

### Implementation Strategy

**Option 1: Replace Pacifica with Cambrian (Recommended)**
- Create `CambrianDataFetcher` class
- Use `/solana/ohlcv/token` endpoint
- Map token symbols to addresses (SOL → So11111111111111111111111111111111111111112)
- Update `StrategyBacktester.fetch_historical_data()` to use Cambrian

**Option 2: Hybrid Approach**
- Use Cambrian for backtesting (historical)
- Use Pacifica for live trading (real-time)

**Option 3: Fallback Chain**
- Try Cambrian first
- Fallback to Pacifica if Cambrian fails
- Best of both worlds

---

## Token Address Mapping

Need to map Pacifica symbols to Solana token addresses:

| Symbol | Solana Token Address |
|--------|---------------------|
| SOL | So11111111111111111111111111111111111111112 |
| ETH | 7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs |
| BTC | 9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E |
| PUMP | (Need to find) |
| ... | ... |

---

## Implementation Plan

### Step 1: Create Cambrian Data Fetcher
```python
class CambrianDataFetcher:
    def fetch_ohlcv(
        self,
        token_address: str,
        after_time: int,  # Unix timestamp (seconds)
        before_time: int,
        interval: str = "15m"
    ) -> pd.DataFrame:
        # Fetch OHLCV from Cambrian
        # Convert to DataFrame format matching Pacifica
```

### Step 2: Update StrategyBacktester
```python
def fetch_historical_data(
    self,
    symbol: str,
    days_back: int = 90,
    interval: str = "15m",
    use_cambrian: bool = True  # New parameter
):
    if use_cambrian:
        return self.cambrian_fetcher.fetch_ohlcv(...)
    else:
        return self.pacifica_fetcher.fetch_market_data(...)
```

### Step 3: Symbol Mapping
```python
SYMBOL_TO_ADDRESS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    # ... add more mappings
}
```

---

## Next Steps

1. ✅ **Analyze Cambrian endpoints** (this document)
2. ⏳ **Create `CambrianDataFetcher` class**
3. ⏳ **Build symbol-to-address mapping**
4. ⏳ **Update `StrategyBacktester` to use Cambrian**
5. ⏳ **Test with 90-day backtest**
6. ⏳ **Compare results with Pacifica data**

---

## References

- [Cambrian OpenAPI Spec](https://opabinia.cambrian.org/openapi.json)
- Cambrian API Docs: `https://docs.cambrian.org/api/v1/solana/ohlcv/token`
- Current Implementation: `rbi_agent/rbi_agent.py` (lines 62-116)
- Pacifica Fetcher: `llm_agent/data/pacifica_fetcher.py`

---

**Status**: Analysis Complete - Ready for Implementation  
**Priority**: High - Will significantly improve backtesting accuracy and efficiency


