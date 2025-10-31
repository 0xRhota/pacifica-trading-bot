# LLM Trading Bot - Data Sources

## All Data Sources (with Attribution)

### 1. Macro Context Sources

**Cambrian Network (Deep42)**
- **What**: Primary macro market analysis and sentiment
- **Endpoint**: `https://deep42.cambrian.network/api/v1/deep42/agents/deep42`
- **API Key**: `doug.ZbEScx8M4zlf7kDn` (Cambrian)
- **Update Frequency**: Cached for 12 hours
- **Label in Prompt**: "Deep42 Market Analysis (Cambrian Network)"

**CoinGecko**
- **What**: Market cap, 24h volume, BTC dominance
- **Endpoint**: `https://api.coingecko.com/api/v3/global`
- **API Key**: None (public endpoint)
- **Update Frequency**: Cached for 12 hours
- **Label in Prompt**: "Quick Metrics (CoinGecko)"

**Alternative.me**
- **What**: Fear & Greed Index
- **Endpoint**: `https://api.alternative.me/fng/?limit=1`
- **API Key**: None (public endpoint)
- **Update Frequency**: Cached for 12 hours
- **Label in Prompt**: "Fear & Greed Index (Alternative.me)"

### 2. Market Data Sources

**Pacifica DEX API**
- **What**: OHLCV candles (15m + 1m), funding rates, current prices
- **Endpoints**: 
  - `/kline` - Historical candles
  - `/info` - Market info including funding rates
  - `/book` - Real-time orderbook (for current prices)
- **API Key**: Agent Key (PACIFICA_API_KEY)
- **Update Frequency**: Fresh on every decision cycle (5 minutes)
- **Label in Prompt**: "Pacifica DEX (Price, Volume, Funding)"

**HyperLiquid**
- **What**: Open Interest data (primary source after Binance 451 errors)
- **Endpoint**: `https://api.hyperliquid.xyz/info`
- **API Key**: None (public endpoint)
- **Update Frequency**: Fresh on every decision cycle
- **Coverage**: 218 markets (92.9% coverage for our 28 symbols)
- **Label in Prompt**: "HyperLiquid/Binance (OI)"

**Binance** (currently failing with 451 errors)
- **What**: Open Interest data (backup)
- **Endpoint**: `https://fapi.binance.com/fapi/v1/openInterest`
- **API Key**: None (public endpoint)
- **Status**: ⚠️ Geo-blocked (HTTP 451)
- **Label in Prompt**: "HyperLiquid/Binance (OI)"

### 3. Calculated Indicators

**Technical Indicators**
- **What**: RSI (14), MACD (12,26,9), SMA (20, 50), Bollinger Bands (20, 2σ)
- **Source**: Calculated from Pacifica OHLCV data
- **Library**: pandas_ta
- **Label in Prompt**: "Calculated (Indicators)"

## Prompt Attribution Summary

The LLM now receives clear source attribution:

```
Deep42 Market Analysis (Cambrian Network):
[Analysis text from Deep42/Cambrian]

Quick Metrics (CoinGecko):
  Market Cap 24h: +2.5% 📈
  BTC Dominance: 58.3%
  Total Volume 24h: $125.4B
  Fear & Greed Index (Alternative.me): 34/100 (Fear) 😰

Market Data (Latest):
Sources: Pacifica DEX (Price, Volume, Funding), HyperLiquid/Binance (OI), Calculated (Indicators)
Symbol     Price        24h Vol   Funding        OI     RSI    MACD  SMA20>50
[Market table with 28 symbols]
```

The LLM is instructed to cite specific sources in its reasoning:
> "Explain your reasoning citing SPECIFIC data sources (e.g., 'Deep42 analysis shows...', 'Fear & Greed index at X...', 'SOL RSI at Y...', 'Funding rate at Z...')"

## Cost Summary

- **Cambrian/Deep42**: Free (using provided API key)
- **CoinGecko**: Free (public API)
- **Alternative.me**: Free (public API)
- **Pacifica**: Free (using API Agent Keys)
- **HyperLiquid**: Free (public API)
- **DeepSeek LLM**: $0.0003 per decision (~$2.70/month for 24/7)

**Total Cost**: ~$2.70/month
