# Phase 0: Pre-Development Validation Report

**Date**: 2025-10-30
**Purpose**: Validate all data sources and APIs work before Phase 1 implementation

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| Pacifica `/info` endpoint | ✅ PASS | Returns all 28 markets in single call |
| Technical indicators library | ✅ PASS | Use `ta` library (not `pandas_ta`) |
| Cambrian batch endpoint | ✅ PASS | `/token-details-multi` works, parameter is `token_addresses` |
| Solana token mapping | ⚠️ PARTIAL | Only 1/28 tokens mapped (3.6% coverage) |
| Open Interest (OI) data | ✅ PASS | 26/28 markets covered (92.9%) via Binance + HyperLiquid |
| DeepSeek API | ⏸️ PENDING | Waiting for API key |

---

## Detailed Findings

### 1. Pacifica API ✅

**Endpoint**: `https://api.pacifica.fi/api/v1/info`

**Result**: PASS - Single API call returns all 28 markets

**Response Format**:
```json
{
  "success": true,
  "data": [
    {
      "symbol": "SOL",
      "funding_rate": "0.0000125",
      "next_funding_rate": "0.0000125",
      "lot_size": "0.01",
      "max_leverage": 20,
      "min_order_size": "10",
      "max_order_size": "1000000",
      ...
    },
    ... (27 more markets)
  ]
}
```

**All 28 Markets**:
ETH, BTC, SOL, PUMP, XRP, HYPE, DOGE, FARTCOIN, ENA, BNB, SUI, kBONK, PENGU, AAVE, LINK, kPEPE, LTC, LDO, UNI, CRV, WLFI, AVAX, ASTER, XPL, 2Z, PAXG, ZEC, MON

**Data Included**:
- ✅ Funding rates (current + next)
- ✅ Lot sizes, tick sizes
- ✅ Min/max order sizes
- ✅ Max leverage per market

**Impact on Architecture**:
- No architectural changes needed
- Single API call sufficient for all market data
- Can fetch once per cycle, not 28 separate calls

---

### 2. Technical Indicators Library ✅

**Library**: `ta` (NOT `pandas_ta` as PRD assumed)
**Version**: 0.11.0
**Python Compatibility**: ✅ Works with Python 3.9

**Required PRD Update**: Change all references from `pandas_ta` to `ta`

**All Required Indicators Available**:
- ✅ SMA (Simple Moving Average) - `ta.trend.SMAIndicator`
- ✅ RSI (Relative Strength Index) - `ta.momentum.RSIIndicator`
- ✅ MACD - `ta.trend.MACD`
- ✅ Bollinger Bands - `ta.volatility.BollingerBands`

**Example Usage**:
```python
import ta
import pandas as pd

# SMA
sma20 = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
sma50 = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()

# RSI
rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

# MACD
macd = ta.trend.MACD(df['close'])
macd_line = macd.macd()
macd_signal = macd.macd_signal()
macd_hist = macd.macd_diff()

# Bollinger Bands
bb = ta.volatility.BollingerBands(df['close'], window=5, window_dev=2)
bb_upper = bb.bollinger_hband()
bb_middle = bb.bollinger_mavg()
bb_lower = bb.bollinger_lband()
```

**Impact on Architecture**:
- No architectural changes
- Need to update import statements in PRD and code
- All indicator calculations work as expected

---

### 3. Cambrian Batch Endpoint ✅

**Endpoint**: `https://opabinia.cambrian.network/api/v1/solana/token-details-multi`

**Result**: PASS - Batch endpoint exists and works

**Parameter Name**: `token_addresses` (comma-separated, NOT `tokens`)

**Example Request**:
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/token-details-multi?token_addresses=So11111111111111111111111111111111111111112,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn"
```

**Response Format**: ClickHouse columnar format
```json
[{
  "columns": [
    {"name": "tokenAddress", "type": "String"},
    {"name": "symbol", "type": "String"},
    {"name": "priceUSD", "type": "Float64"},
    {"name": "volume24hUSD", "type": "Float64"},
    {"name": "buy24hCount", "type": "UInt64"},
    {"name": "sell24hCount", "type": "UInt64"},
    ... (more columns)
  ],
  "data": [
    ["So11111111111111111111111111111111111111112", "SOL", 196.5, 2300000000, ...],
    ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USDC", 1.0, ...],
    ...
  ]
}]
```

**Data Available**:
- ✅ 24h volume (USD)
- ✅ Buy/sell counts
- ✅ Price (USD)
- ✅ Trade counts (1h, 24h, 7d)
- ✅ Last trade timestamp

**Impact on Architecture**:
- Single batch call can fetch multiple tokens
- Need to handle ClickHouse columnar format (columns + data array)
- Much more efficient than individual calls

---

### 4. Solana Token Address Mapping ⚠️

**Status**: PARTIAL COVERAGE

**Coverage**: 1/28 tokens mapped (3.6%)

**Mapped Tokens**:
- ✅ SOL: `So11111111111111111111111111111111111111112`

**Unmapped Tokens** (27/28):
ETH, BTC, PUMP, XRP, HYPE, DOGE, FARTCOIN, ENA, BNB, SUI, kBONK, PENGU, AAVE, LINK, kPEPE, LTC, LDO, UNI, CRV, WLFI, AVAX, ASTER, XPL, 2Z, PAXG, ZEC, MON

**Why This Is a Problem**:
- Cambrian API requires Solana token addresses
- Most Pacifica markets are wrapped tokens (BTC, ETH) or newer meme coins
- We don't have addresses for 96% of markets

**Mitigation Strategies**:

**Option 1: OHLCV + Indicators Only (MVP)**
- Use Pacifica OHLCV data
- Calculate technical indicators locally
- Use Pacifica funding rates
- Skip Cambrian token metrics for unmapped tokens
- **Still gives LLM plenty of data**: Price, volume, RSI, MACD, SMA, funding rates

**Option 2: Incremental Address Lookup**
- Research addresses for top 10 volume tokens
- Add to mapping table as we find them
- Gradually improve coverage post-MVP

**Option 3: Skip Cambrian Entirely for MVP**
- Phase 1 MVP uses only Pacifica data
- Add Cambrian in Phase 4 when we have better mapping

**Recommended Approach**: Option 1 (OHLCV + indicators only)
- MVP is still viable with 7 data points per market:
  1. Current price (OHLCV close)
  2. Volume (OHLCV)
  3. SMA20 / SMA50 (trend)
  4. RSI (momentum)
  5. MACD (momentum)
  6. Bollinger Bands (volatility)
  7. Funding rate (sentiment)

**Impact on Architecture**:
- Add graceful fallback: if no Solana address, skip Cambrian data
- Log unmapped tokens for future lookup
- MVP can launch with just Pacifica + indicators

---

### 5. Open Interest (OI) Data ✅

**Status**: PASS - 92.9% coverage

**Coverage**: 26/28 markets covered

**Data Sources**:
- **Binance Futures API**: 19 markets (priority source)
- **HyperLiquid API**: 26 markets (fallback for missing Binance data)

**Unavailable**: kBONK, kPEPE (2/28 markets)

**API Endpoints**:

**Binance**:
```bash
curl "https://fapi.binance.com/fapi/v1/openInterest?symbol=SOLUSDT"
# Response: {"symbol":"SOLUSDT","openInterest":"8053270.46","time":1761794989895}
```

**HyperLiquid**:
```bash
curl -X POST "https://api.hyperliquid.xyz/info" \
  -H "Content-Type: application/json" \
  -d '{"type": "metaAndAssetCtxs"}'
# Response: [meta, [{"openInterest": "35323.1222", ...}, ...]]
```

**Symbol Mapping**:
```python
# Binance: Pacifica → USDT perpetuals
"SOL" → "SOLUSDT"
"BTC" → "BTCUSDT"
"ETH" → "ETHUSDT"
# ... 19 total

# HyperLiquid: Direct 1:1 mapping (except kBONK/kPEPE)
"SOL" → "SOL"
"PUMP" → "PUMP"
"FARTCOIN" → "FARTCOIN"
# ... 26 total
```

**Data Quality**:
- ✅ Real-time updates (timestamp included)
- ✅ High precision values
- ✅ Reliable APIs (no auth required for Binance, no key for HyperLiquid public endpoint)
- ✅ Fast response times (<1 second)

**Integration Strategy**:
1. **Binance first** (faster, more established exchanges)
2. **HyperLiquid fallback** for tokens not on Binance (PUMP, FARTCOIN, WLFI, ASTER, XPL, 2Z, MON)
3. **Single batch call** to HyperLiquid (fetches all 218 markets at once)
4. **Graceful handling** for kBONK/kPEPE (log warning, proceed without OI)

**Example OI Values** (from test):
- BTC: 78,818 contracts
- SOL: 8,055,793 contracts
- PUMP: 35,443,580,570 contracts (meme coin)
- DOGE: 1,519,021,233 contracts

**Impact on Architecture**:
- Add `OIDataFetcher` class to data pipeline
- Single API call to HyperLiquid per cycle (not per symbol)
- OI data included in LLM prompt table
- 2 markets without OI won't block MVP (94% coverage sufficient)

---

### 6. DeepSeek API ⏸️

**Status**: PENDING (need API key)

**Required Before Phase 2**:
- Obtain DeepSeek API key from https://platform.deepseek.com/
- Test basic completion endpoint
- Verify response format
- Confirm context window size (for 28 market prompt)
- Test response parsing with forced format

**Once API key obtained, test**:
```python
import openai  # DeepSeek is OpenAI-compatible

client = openai.OpenAI(
    api_key="<DEEPSEEK_KEY>",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "Test prompt"}
    ],
    temperature=0.1,
    max_tokens=50
)
```

---

## Architecture Decisions Based on Findings

### ✅ No Changes Needed:
1. Pacifica `/info` endpoint works exactly as expected
2. Technical indicators library available (just different name)
3. Cambrian batch endpoint exists and works

### ⚠️ Adjustments Needed:
1. **Library name**: Change `pandas_ta` → `ta` in all docs and code
2. **Cambrian strategy**: Graceful fallback for unmapped tokens
3. **MVP scope**: Launch with Pacifica + indicators only, Cambrian optional

### 🔴 Blockers:
1. **DeepSeek API key**: Required before Phase 2 can start

---

## Revised MVP Data Pipeline

**Phase 1 MVP** (confirmed feasible):
```
For each of 28 Pacifica markets:
1. Fetch OHLCV from Pacifica /kline
2. Calculate indicators locally (SMA, RSI, MACD, BBands)
3. Fetch funding rate from Pacifica /info (already have from step 1)
4. TRY fetch Cambrian data (graceful skip if no address)
5. Aggregate into summary table for LLM
```

**Data Per Market** (8-11 columns):
- Price (from OHLCV)
- Volume 24h (from OHLCV)
- SMA20/SMA50 trend indicator
- RSI (momentum)
- MACD (momentum)
- Bollinger Bands (volatility)
- Funding rate (sentiment)
- **Open Interest** (from Binance/HyperLiquid) - **92.9% coverage**
- *[Optional]* Cambrian volume 24h (if address available)
- *[Optional]* Buy/sell ratio (if address available)

**Estimated Prompt Size**:
- 28 markets × 11 columns = 308 data points
- Formatted as ASCII table ≈ 3500 characters
- Token estimate: ~875 tokens (well within limits)

---

## Recommendations

### Before Phase 1:
1. ✅ Update PRD: Change `pandas_ta` to `ta`
2. ✅ Add token mapping module to codebase
3. ✅ Update PRD: Cambrian is optional, not required
4. ⏸️ Obtain DeepSeek API key

### Phase 1 Implementation:
1. Build data fetcher with graceful Cambrian fallback
2. Test with all 28 markets (Cambrian will only work for SOL)
3. Verify indicator calculations work on real OHLCV data
4. Ensure prompt size is reasonable (<4000 tokens)

### Post-MVP:
1. Research Solana addresses for high-volume tokens
2. Add addresses incrementally to mapping table
3. Cambrian coverage will improve organically

---

## Conclusion

**MVP is VIABLE** with these findings:

✅ **Can fetch**: All 28 Pacifica markets
✅ **Can calculate**: All required indicators (SMA, RSI, MACD, BBands)
✅ **Can batch**: Cambrian queries (when addresses available)
✅ **Can fetch OI**: 26/28 markets via Binance + HyperLiquid (92.9% coverage)
⚠️ **Limited**: Cambrian data (only SOL initially), OI missing for kBONK/kPEPE
⏸️ **Pending**: DeepSeek API access

**Alpha Arena Data Parity Achieved**:
- ✅ Funding rates
- ✅ Open Interest (OI) - **NEW**
- ✅ Volume
- ✅ RSI
- ✅ MACD
- ✅ EMA/SMA

**No architectural blockers identified.** Ready to proceed with Phase 1 once DeepSeek key is obtained.
