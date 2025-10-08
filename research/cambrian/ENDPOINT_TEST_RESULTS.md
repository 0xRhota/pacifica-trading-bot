# Cambrian API Endpoint Test Results

## Perp Risk Engine ✅ WORKING

**Endpoint**: `https://risk.cambrian.network/api/v1/perp-risk-engine`

**Test**: SOL long position, $235 entry, 5x leverage, 1 day horizon

**Results**:
```json
{
  "status": "success",
  "riskProbability": 0.0,
  "liquidationPrice": 187.97,
  "entryPrice": 235.0,
  "volatility": 0.5322,
  "drift": 5.45,
  "priceChangeNeeded": 0.2001,
  "sigmasAway": 7.18,
  "simulationDetails": {
    "totalSimulations": 10000,
    "liquidatedPaths": 0,
    "dataPointsUsed": 670
  }
}
```

**What This Means**:
- **0% liquidation risk** for 5x SOL long at $235 over 1 day
- Liquidation price: **$187.97** (need -20% move to get liquidated)
- **7.18 standard deviations** away from liquidation = extremely safe
- Volatility: 53% annualized (high but typical for crypto)

**Trading Signal Value**: HIGH
- Can use this to determine safe leverage levels
- Real-time liquidation risk assessment
- Monte Carlo simulation (10,000 paths)

---

## Deep42 Social Intelligence ❌ NOT FOUND

**Tested Endpoints**:
1. `/api/v1/deep42/social-data/token-analysis` → 404
2. `/api/v1/deep42/social-data/alpha-tweet-detection` → 404
3. `/api/v1/deep42/social-data/trending-momentum` → 404

**Status**: These endpoints may:
- Not be live yet
- Have different URL structure
- Be under different path (not `/api/v1/`)
- Require different authentication

**Need to explore**:
- Check llms.txt for deep42
- Ask about Deep42 endpoint structure
- Verify if Deep42 is production-ready

---

## On-Chain Data ✅ CONFIRMED AVAILABLE

**Available per previous testing**:
- Trade statistics (buy/sell ratio)
- OHLCV candlestick data (1m, 5m, 15m, 1h, 4h, 1d)
- Trending tokens
- Trader leaderboard
- Token holders
- Wallet balances

**Chains Supported**:
- Solana
- Base (EVM chain)

---

## What We Can Use Right Now

### 1. Perp Risk Engine (HIGHEST VALUE)
```python
# Before opening position
risk_data = check_liquidation_risk(
    token="SOL",
    entry_price=235,
    leverage=5,
    direction="long",
    horizon="1d"
)

if risk_data['riskProbability'] > 0.05:  # 5% threshold
    # Reduce leverage or skip trade
    pass
```

**Benefits**:
- Prevent over-leveraged positions
- Real-time risk assessment
- Data-driven leverage decisions

### 2. On-Chain Trading Data (HIGH VALUE)
Already tested and working:
- Buy/sell pressure (0.19 ratio for SOL = bearish)
- Volume trends
- Price action (OHLCV)

### 3. Deep42 Social Data (UNKNOWN)
Need to find correct endpoint structure.

---

## Next Steps

1. **Immediate**: Find Deep42 endpoint structure
   - Check `https://docs.cambrian.org/api/v1/deep42/llms.txt`
   - Try different URL patterns
   - Ask user about Deep42 status

2. **Test Base Chain Data**
   - OHLCV on Base
   - Compare Solana vs Base data quality

3. **Integration Planning** (after user approval)
   - Add perp risk engine to position sizing
   - Use buy/sell ratio as entry filter
   - Combine multiple signals
