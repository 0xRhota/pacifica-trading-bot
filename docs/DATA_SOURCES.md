# Data Sources Reference

**Purpose:** Comprehensive reference for all data sources available for LLM trading agent implementation.

---

## 1. CAMBRIAN API

**Base URL:** `https://opabinia.cambrian.network/api/v1`
**API Key:** `YOUR_CAMBRIAN_API_KEY` (set in .env as `CAMBRIAN_API_KEY`)
**Authentication:** `-H "X-API-Key: YOUR_CAMBRIAN_API_KEY"`
**Docs Pattern:** Each endpoint has `/llms.txt` for AI-readable documentation
**Response Format:** ClickHouse columnar format (columns + data arrays)

### Deep42 AI Agent - Social Sentiment & Blockchain Intelligence

**Base URL:** `https://deep42.cambrian.network/api/v1/deep42/agents/deep42`
**Purpose:** Comprehensive blockchain intelligence including market analysis, developer activity, social sentiment, and research

**Authentication:** `-H "X-API-KEY: YOUR_CAMBRIAN_API_KEY"`

**Request Parameters:**
- `question` (required): Blockchain inquiry (max 10,000 chars)
  - Default: "What are the top trending tokens on Solana?"
- `continue_chat_id` (optional): UUID from previous response to continue conversation

**Response Structure:**
- `answer`: AI-generated response with formatted tables, analysis, insights
- `docs_urls`: Array of relevant documentation links
- `chat_id`: UUID for continuing dialogue sessions

**Example - Trending Tokens:**
```bash
curl -X GET "https://deep42.cambrian.network/api/v1/deep42/agents/deep42?question=What%20are%20the%20top%20trending%20tokens%20on%20Solana%3F" \
  -H "X-API-KEY: YOUR_CAMBRIAN_API_KEY" \
  -H "Content-Type: application/json"
```

**Example - Multi-Domain Analysis:**
```bash
curl -X GET "https://deep42.cambrian.network/api/v1/deep42/agents/deep42?question=Analyze%20Jupiter%20Exchange:%20development%20activity,%20social%20buzz,%20and%20trading%20metrics" \
  -H "X-API-KEY: YOUR_CAMBRIAN_API_KEY" \
  -H "Content-Type: application/json"
```

**Use Cases:**
- Social sentiment analysis for tokens
- Developer activity monitoring
- Alpha tweet detection
- Sentiment shift identification
- Social momentum tracking

**Docs:** https://docs.cambrian.org/api/v1/deep42/agents/deep42/llms.txt

---

### Token Metrics

#### `/solana/token-details` - Single Token Details
**Purpose:** Comprehensive token metrics (volume, price, holders, supply)

**Parameters:**
- `token_address` (required): Token mint address

**Returns:**
- Token metadata: address, symbol, name, decimals
- Price: current USD price, last trade timestamp
- Volume: 1h/24h/7d volumes (tokens + USD)
- Trade counts: 1h/24h/7d
- Buy/Sell split: 24h buy/sell counts and volumes
- Holders: holder count
- Supply: total supply, FDV

**Example:**
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/token-details?token_address=So11111111111111111111111111111111111111112" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn" \
  -H "Content-Type: application/json"
```

**Docs:** https://docs.cambrian.org/api/v1/solana/token-details/llms.txt

---

#### `/solana/token-details-multi` - Batch Token Details
**Purpose:** Get multiple token details in single API call

**Parameters:**
- `token_addresses` (required): Comma-separated token addresses

**Example:**
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/token-details-multi?token_addresses=So11111111111111111111111111111111111111112,DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn"
```

---

#### `/solana/tokens/security` - Security & Risk Metrics
**Purpose:** Risk assessment, holder concentration, volatility

**Parameters:**
- `token_address` (required): Token to analyze

**Returns:**
- Holder distribution: count, top 5/10/20/50 concentration %
- Balance metrics: bottom 10%, median, top 10%
- Transaction metrics: 24h tx count, unique active accounts
- Volatility: 30-day volatility, price range, max/min ratio
- Security score: 0-100 overall risk assessment

**Example:**
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/tokens/security?token_address=So11111111111111111111111111111111111111112" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn"
```

---

#### `/solana/tokens/holders` - Token Holders List
**Purpose:** List holders with balances

**Parameters:**
- `program_id` (required): Token mint address
- `limit` (optional): 1-1000, default 100
- `offset` (optional): Pagination

**Returns:**
- account: wallet address
- balanceRaw: raw token balance
- balanceUi: human-readable balance
- balanceUSD: USD value

**Example:**
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/tokens/holders?program_id=DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263&limit=10" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn"
```

---

### Price Data

#### `/solana/price-current` - Current Price (Single)
**Purpose:** Real-time USD price

**Parameters:**
- `token_address` (required)

**Returns:** tokenAddress, symbol, priceUSD

---

#### `/solana/price-multi` - Current Price (Batch)
**Purpose:** Batch current prices

**Parameters:**
- `token_addresses` (required): Comma-separated

---

#### `/solana/price-hour` - Historical Price (Intervals)
**Purpose:** Aggregated price at intervals

**Parameters:**
- `token_address` (required)
- `interval` (required): 1H, 2H, 4H, 6H, 8H, 12H, 1D, 3D, 1W, 1M
- `limit`, `offset` (optional)

**Returns:**
- tokenAddress, tokenSymbol, intervalStart
- priceUSD: average for interval
- datapoints: number of data points averaged

---

#### `/solana/price-volume/single` - Price + Volume with Changes
**Purpose:** Combined price/volume with percentage changes

**Parameters:**
- `token_address` (required)
- `timeframe` (required): 1h, 2h, 4h, 8h, 24h

**Returns:**
- tokenAddress, symbol, priceUSD, updateUnixTime
- volumeUSD, volumeChangePercent, priceChangePercent, priceChangeUSD

**Example:**
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/price-volume/single?token_address=So11111111111111111111111111111111111111112&timeframe=24h" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn"
```

---

### OHLCV (Candlestick) Data

#### `/solana/ohlcv/token` - Token OHLCV (All Venues)
**Purpose:** OHLCV aggregated across all trading venues

**Parameters:**
- `token_address` (required)
- `after_time` (required): Unix timestamp (seconds)
- `before_time` (required): Unix timestamp (seconds)
- `interval` (required): 1m, 5m, 15m, 1h, 4h, 1d

**Returns:**
- openPrice, highPrice, lowPrice, closePrice (USD)
- volume (USD), volumeToken (native units)
- unixTime, interval, tokenAddress

**Note:** Limited to current year data

**Example:**
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/ohlcv/token?token_address=So11111111111111111111111111111111111111112&after_time=1759858000&before_time=1759865709&interval=15m" \
  -H "X-API-Key: doug.ZbEScx8M4zlf7kDn" \
  -H "Content-Type: application/json"
```

---

#### `/solana/ohlcv/base-quote` - Base/Quote Pair OHLCV
**Purpose:** OHLCV for specific token pairs

**Parameters:**
- `base_address` (required): Base token
- `quote_address` (required): Quote token
- `after_time`, `before_time` (required): Unix timestamps
- `interval` (required): 1m, 5m, 15m, 1h, 4h, 1d

**Returns:**
- openPrice, highPrice, lowPrice, closePrice (quote units)
- volume (USD), volumeBase (base units)
- tradeCount, poolCount, providerCount

---

### DEX Liquidity Pool Data

#### `/solana/raydium-clmm/pool` - Raydium Concentrated Liquidity
**Purpose:** Metrics for Raydium CLMM pools

**Parameters:**
- `pool_address` (required)

**Returns:**
- Pool info: token0/token1, fee tier, tick spacing
- Pricing: price, sqrtPriceX64, tick
- Liquidity: tvlToken0, tvlToken1, tvlUSD
- Activity: volume24h, fees24h, apr24h
- Risk: priceVolatility, utilization24h

---

#### `/solana/meteora-dlmm/pool-multi` - Meteora DLMM (Batch)
**Purpose:** Batch Meteora pool data

**Parameters:**
- `pool_addresses` (required): Comma-separated

**Returns:**
- Pool info: token0/token1, bin step, fee tier, active bin
- Pricing: currentPrice, token0/1 USD prices
- Liquidity: tvlToken0, tvlToken1, tvlUSD
- Activity: volume24h, fees24h, apr24h, swaps24h
- Risk: priceVolatility, utilization24h

---

### Cambrian Response Format

All endpoints return ClickHouse columnar format:
```json
[{
  "columns": [
    {"name": "fieldName", "type": "Type"},
    ...
  ],
  "data": [
    [value1, value2, ...],  // Row 1
    [value1, value2, ...]   // Row 2
  ],
  "rows": 2
}]
```

**Data Freshness:**
- 15m candles: UP-TO-DATE (0.046% divergence from Pacifica)
- Historical: Limited to current year

---

## 2. PACIFICA API

**Base URL:** `https://api.pacifica.fi/api/v1`
**Account:** `YOUR_ACCOUNT_PUBKEY`
**Authentication:** API Agent Keys (no private key required)
**Docs:** https://docs.pacifica.fi/api-documentation

### Market Data

#### `/kline` - OHLCV Candles
**Purpose:** Historical candlestick data

**Parameters:**
- `symbol` (required): Token symbol (SOL, BTC, ETH)
- `interval` (required): 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d
- `start_time` (required): Unix timestamp (milliseconds)
- `limit` (optional): Number of candles

**Returns:**
- timestamp (ms), open, high, low, close, volume

**Example:**
```bash
curl "https://api.pacifica.fi/api/v1/kline?symbol=SOL&interval=15m&start_time=1759860000000&limit=10"
```

**Data Freshness:**
- 15m candles: UP-TO-DATE (0.025% divergence from orderbook)
- Latency: <1 second

---

#### `/book` - Orderbook
**Purpose:** Real-time order book (bids/asks)

**Parameters:**
- `symbol` (required)
- `depth` (optional): Orderbook depth

**Data Freshness:** INSTANT (<1 second latency)

---

#### `/price` - Current Prices
**Purpose:** Current market prices

**Parameters:**
- `symbol` (optional): Specific symbol, or all if omitted

---

### Account & Trading

#### `/positions` - Account Positions
**Purpose:** Get open positions for account

**Parameters:**
- `account` (required): Account address

---

#### `/orders/create_market` - Place Market Order
**Purpose:** Execute market orders

**Parameters:**
- Order details (requires API signature)

**Note:** Uses API Agent Keys for signing (no wallet private key needed)

---

## 3. MOON DEV DATA REQUIREMENTS

**Core Philosophy** (from Jay A - Alpha Arena winner):
> "There is macro context encoded in quantitative data. We feed them funding rates, OI, volume, RSI, MACD, EMA, etc to capture 'state' of market at different granularities. They decide the 'style' of trading."

Based on reverse-engineering Moon Dev AI trading agent:

### Data Inputs to LLM

1. **OHLCV Candles** (pandas DataFrame → ASCII table)
   - Default: 1H timeframe, 3 days back (~72 bars)
   - Columns: timestamp, open, high, low, close, volume

2. **Technical Indicators** (calculated with pandas_ta)
   - SMA20, SMA50
   - RSI (14-period)
   - MACD (12,26,9) with histogram + signal
   - Bollinger Bands (5,2)

3. **External Data**
   - **Funding rates** (HyperLiquid API) - Annual % rate
   - **BTC trend** as market context (15m candles + 20 SMA)
   - **Token metrics** (Birdeye API):
     - buy1h, sell1h, trade1h - Volume metrics
     - priceChangesXhrs - Price changes
     - uniqueWallet24h, v24hUSD - Trading metrics
     - liquidity, mc - Market cap
     - watch, view24h - Social metrics

4. **Prompt Format**
   - Shows last 10 bars + full dataset as ASCII table
   - Simple instruction: "Respond with ONLY: Buy, Sell, or Do Nothing"

### Moon Dev Data Flow

```
API FETCH (HyperLiquid/Aster/Solana)
  ↓
_get_ohlcv() → Raw JSON
  ↓
_process_data_to_df() → pandas DataFrame (O,H,L,C,V)
  ↓
add_technical_indicators() → Add SMA, RSI, MACD, BBands
  ↓
_format_market_data_for_swarm() → ASCII table string
  ↓
PROMPT + formatted_data → Send to 6 LLM models
  ↓
Vote aggregation → Consensus decision
```

---

## 4. GAP ANALYSIS

### ✅ Available from Cambrian + Pacifica

| Data Type | Source | Endpoint |
|---|---|---|
| Token volume (1h/24h/7d) | Cambrian | `/solana/token-details` |
| Price + changes | Cambrian | `/solana/price-volume/single` |
| OHLCV candles | Both | Cambrian `/ohlcv/token` or Pacifica `/kline` |
| Holder count + distribution | Cambrian | `/solana/tokens/security` |
| Security/risk scores | Cambrian | `/solana/tokens/security` |
| Liquidity/TVL | Cambrian | Pool endpoints |
| Market cap/FDV | Cambrian | `/solana/token-details` |

### ✅ NOW Available

| Data Type | Source | Status |
|---|---|---|
| **Social sentiment** | Cambrian Deep42 | ✅ Available via AI agent |
| **Funding rates** | Multiple free sources | ✅ See Funding Rates section below |

---

## 4.5. FUNDING RATES

### Recommended Sources (All FREE)

#### 1. Binance API (Best Overall)
**Endpoint:** `https://fapi.binance.com/fapi/v1/fundingRate`
**Authentication:** None required
**Parameters:**
- `symbol`: Trading pair (e.g., SOLUSDT, BTCUSDT, ETHUSDT)
- `startTime`, `endTime` (optional): Unix timestamps (milliseconds)
- `limit` (optional): Default 100, max 1000

**Example:**
```bash
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT&limit=10"
```

**Response:**
```json
[
  {
    "symbol": "SOLUSDT",
    "fundingRate": "0.00010000",
    "fundingTime": 1640995200000
  }
]
```

**Update Frequency:** Every 8 hours (00:00, 08:00, 16:00 UTC)
**Data History:** Years of historical data
**Rating:** 10/10 - Industry standard

---

#### 2. Drift Protocol (Solana Native)
**Endpoint:** `wss://dlob.drift.trade` (WebSocket)
**Authentication:** None required
**Purpose:** Real-time Solana perpetuals funding rates

**Update Frequency:** Hourly
**Data:** Pure on-chain Solana data
**Rating:** 9/10 - Best for Solana-native

---

#### 3. Bybit API
**Endpoint:** `https://api.bybit.com/v5/market/funding/history`
**Authentication:** None required
**Parameters:**
- `category`: linear
- `symbol`: Trading pair (SOLUSDT, etc.)
- `limit`: Max 200

**Example:**
```bash
curl "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=SOLUSDT&limit=10"
```

**Update Frequency:** Every 8 hours
**Rating:** 9/10

---

#### 4. CoinGlass (Aggregator)
**Website:** https://www.coinglass.com/funding/SOL
**Purpose:** Aggregated funding rate data across exchanges
**Data:** Visual charts + historical data
**Rating:** 8/10 - Good for analysis, not for automated trading

---

#### 5. Pacifica API (Status Unknown)
**Need to verify:** Contact Pacifica support to check if they have funding rate endpoints
**Likely path:** `/api/v1/funding` or `/api/v1/funding-rate`

---

## 5. TOKEN ADDRESSES (Solana)

- **SOL (Wrapped)**: `So11111111111111111111111111111111111111112`
- **BONK**: `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`
- **BTC/ETH**: Need to look up wrapped addresses

---

## 6. IMPLEMENTATION NOTES

### Data Alignment
- Cambrian + Pacifica align within 0.05% divergence
- Both provide up-to-date 15m candles
- Use Pacifica for real-time orderbook, Cambrian for historical/metrics

### API Rate Limits
- TBD: Document rate limits for both APIs

### Data Freshness
- Cambrian historical: Current year only
- Pacifica: Real-time + historical (check limits)

---

## 7. SETUP INSTRUCTIONS

### Adding Cambrian API Key to .env

1. **Open `.env` file** in project root:
```bash
nano .env
# or
code .env
```

2. **Add the following line:**
```bash
# Cambrian API Key (for token metrics, social data, funding rates)
CAMBRIAN_API_KEY=your_api_key_here
```

3. **Save and close**

4. **Verify it's in .gitignore:**
```bash
grep ".env" .gitignore
# Should show: .env
```

### Testing Cambrian APIs

#### Test 1: Token Details (SOL)
```bash
export CAMBRIAN_API_KEY="your_key_here"

curl -X GET "https://opabinia.cambrian.network/api/v1/solana/token-details?token_address=So11111111111111111111111111111111111111112" \
  -H "X-API-Key: $CAMBRIAN_API_KEY" \
  -H "Content-Type: application/json"
```

**Expected:** JSON with SOL price, volume, holder count, etc.

---

#### Test 2: Deep42 Social Sentiment
```bash
curl -X GET "https://deep42.cambrian.network/api/v1/deep42/agents/deep42?question=What%20are%20the%20top%20trending%20tokens%20on%20Solana%3F" \
  -H "X-API-KEY: $CAMBRIAN_API_KEY" \
  -H "Content-Type: application/json"
```

**Expected:** JSON with `answer` (formatted text), `docs_urls` (array), `chat_id` (UUID)

---

#### Test 3: OHLCV Data (15m candles)
```bash
# Get current timestamp
START_TIME=$(date -u -d '2 hours ago' +%s)
END_TIME=$(date -u +%s)

curl -X GET "https://opabinia.cambrian.network/api/v1/solana/ohlcv/token?token_address=So11111111111111111111111111111111111111112&after_time=$START_TIME&before_time=$END_TIME&interval=15m" \
  -H "X-API-Key: $CAMBRIAN_API_KEY" \
  -H "Content-Type: application/json"
```

**Expected:** ClickHouse format with columns + data arrays

---

#### Test 4: Security Metrics
```bash
curl -X GET "https://opabinia.cambrian.network/api/v1/solana/tokens/security?token_address=So11111111111111111111111111111111111111112" \
  -H "X-API-Key: $CAMBRIAN_API_KEY"
```

**Expected:** Holder concentration, volatility, security score

---

### Testing Funding Rate APIs (No Auth Required)

#### Test 1: Binance - SOL Funding Rate
```bash
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT&limit=5"
```

**Expected:**
```json
[
  {
    "symbol": "SOLUSDT",
    "fundingRate": "0.00010000",
    "fundingTime": 1640995200000
  }
]
```

---

#### Test 2: Bybit - SOL Funding Rate
```bash
curl "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=SOLUSDT&limit=5"
```

**Expected:** JSON with funding rate history

---

### Python Integration Example

```python
import os
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()
CAMBRIAN_API_KEY = os.getenv("CAMBRIAN_API_KEY")

# Test Cambrian Token Details
def test_cambrian_token_details():
    url = "https://opabinia.cambrian.network/api/v1/solana/token-details"
    params = {
        "token_address": "So11111111111111111111111111111111111111112"
    }
    headers = {
        "X-API-Key": CAMBRIAN_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, params=params, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Data: {response.json()}")

# Test Deep42 Social Sentiment
def test_deep42_social():
    url = "https://deep42.cambrian.network/api/v1/deep42/agents/deep42"
    params = {
        "question": "What are the top trending tokens on Solana?"
    }
    headers = {
        "X-API-KEY": CAMBRIAN_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    print(f"Answer: {data.get('answer')}")
    print(f"Chat ID: {data.get('chat_id')}")

# Test Binance Funding Rate (no auth)
def test_binance_funding():
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {
        "symbol": "SOLUSDT",
        "limit": 5
    }

    response = requests.get(url, params=params)
    print(f"Funding Rates: {response.json()}")

if __name__ == "__main__":
    print("Testing Cambrian Token Details...")
    test_cambrian_token_details()

    print("\nTesting Deep42 Social Sentiment...")
    test_deep42_social()

    print("\nTesting Binance Funding Rates...")
    test_binance_funding()
```

---

## NEXT STEPS

1. ✅ Document Cambrian + Pacifica endpoints
2. ✅ Research funding rate sources
3. ✅ Confirm social sentiment data source (Deep42)
4. ⏳ Add CAMBRIAN_API_KEY to .env
5. ⏳ Run test scripts to verify API access
6. ⏳ Build data aggregation pipeline
