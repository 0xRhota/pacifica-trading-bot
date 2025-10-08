# Cambrian API Integration Plan for Pacifica Bot

## Overview
Integrate Cambrian's on-chain data to enhance Pacifica perps trading signals, focusing on buy/sell pressure and volume analysis for major tokens.

## Current Cambrian Data Available

### 1. Trade Statistics (HIGH VALUE)
**What it provides**:
- Buy vs Sell transaction counts
- Buy/Sell volume ratio
- 24h volume in USD
- Trading activity levels

**Current SOL Example**:
```python
{
  "buy_count": 2,590,613,
  "sell_count": 7,812,604,
  "total_volume_usd": 5,856,493,412,
  "buy_to_sell_ratio": 0.19  # BEARISH
}
```

**Trading Signal Logic**:
- Ratio > 1.1 = BULLISH (more buying pressure)
- Ratio < 0.9 = BEARISH (more selling pressure)
- Ratio 0.9-1.1 = NEUTRAL

### 2. OHLCV Price Data (HIGH VALUE)
**What it provides**:
- Open, High, Low, Close prices
- Volume (USD and token units)
- Trade count per interval
- Multiple timeframes: 1m, 5m, 15m, 1h, 4h, 1d

**Use Cases**:
- Detect price trends
- Measure volatility
- Confirm volume spikes
- Support/resistance levels

### 3. Trending Tokens (MEDIUM VALUE)
**What it provides**:
- Price change % (24h)
- Volume rankings
- Market cap and liquidity
- Holder count

**Use Cases**:
- Discover momentum plays
- Confirm major token trends
- Filter out low-liquidity tokens

## Integration Strategy

### Phase 1: Basic Signal Integration (IMMEDIATE)
Add Cambrian buy/sell ratio to existing Pacifica bot entry logic:

```python
# In live_bot.py, before opening position:

from research.cambrian.cambrian_client import CambrianClient

cambrian = CambrianClient()

# Get momentum signal
signal = cambrian.get_momentum_signal(symbol)

# Filter trades based on signal
if signal['signal'] == 'BEARISH' and BotConfig.LONGS_ONLY:
    logger.info(f"⚠️  Skipping {symbol} - Cambrian shows BEARISH signal (ratio: {signal['buy_to_sell_ratio']:.2f})")
    return

# Proceed with order placement...
```

**Benefits**:
- Avoid opening longs during heavy selling pressure
- Reduce losses from fighting the trend
- Simple integration, minimal code changes

### Phase 2: Volume Confirmation (NEXT)
Require high volume for signal validity:

```python
# Check volume is above threshold
volume_24h = signal['volume_24h_usd']
min_volume = 100_000_000  # $100M minimum

if volume_24h < min_volume:
    logger.info(f"⚠️  Low volume ({volume_24h:,.0f}), skipping")
    return
```

### Phase 3: Advanced Signals (FUTURE)
Combine multiple data points:

1. **Trend Detection**:
   - Use OHLCV to detect uptrend/downtrend
   - Confirm with buy/sell ratio
   - Only trade WITH the trend

2. **Volume Spike Detection**:
   - Compare current volume to historical average
   - High volume + strong signal = higher confidence

3. **Smart Money Tracking**:
   - Use trader leaderboard data
   - Follow top traders' positions
   - Avoid tokens with smart money exiting

## Implementation Files

### Created:
1. `research/cambrian/cambrian_client.py` - API client with trading signals
2. `research/cambrian/test_api.py` - API exploration script
3. `research/cambrian/FINDINGS.md` - Complete research notes
4. `research/cambrian/.env` - API credentials (gitignored)
5. `research/cambrian/README.md` - Project overview

### To Create:
1. `research/cambrian/signals.py` - Advanced signal logic
2. Update `live_bot.py` - Integrate Cambrian signals
3. Update `config.py` - Add Cambrian settings

## Configuration Required

Add to `config.py`:
```python
# Cambrian API
USE_CAMBRIAN_SIGNALS = True
CAMBRIAN_MIN_VOLUME_USD = 100_000_000  # $100M minimum
CAMBRIAN_BEARISH_THRESHOLD = 0.9
CAMBRIAN_BULLISH_THRESHOLD = 1.1

# Signal requirements
REQUIRE_BULLISH_SIGNAL = False  # Start with filter only
SKIP_ON_BEARISH = True  # Skip trades on bearish signals
```

## Testing Plan

1. **Backtest Signals**:
   - Pull historical Cambrian data
   - Compare past signals to actual outcomes
   - Measure win rate improvement

2. **Paper Trading**:
   - Run bot with Cambrian signals (no real orders)
   - Monitor signal accuracy
   - Tune thresholds

3. **Live Trading (Small Size)**:
   - Enable Cambrian filtering
   - Monitor for 1-2 days
   - Compare performance vs baseline

## Expected Improvements

### Conservative Estimate:
- **Win Rate**: +5-10% (by avoiding bad entries)
- **Reduced Losses**: Skip trades during heavy selling
- **Better Timing**: Enter when momentum aligns

### Metrics to Track:
- Trades filtered by Cambrian (count)
- Win rate with vs without signals
- Average P&L per trade
- Max drawdown reduction

## Token Address Discovery

Need to find Solana addresses for:
- ✅ SOL - `So11111111111111111111111111111111111111112`
- ✅ USDC - `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- ❌ BTC (Wrapped)
- ❌ ETH (Wrapped)
- ❌ PENGU
- ❌ XPL
- ❌ HYPE
- ❌ ASTER

Can use trending tokens endpoint to discover addresses.

## Next Steps

1. **Immediate**: Test basic signal integration in dry-run mode
2. **This Week**: Add Cambrian filter to live bot
3. **Next Week**: Measure performance improvement
4. **Future**: Build advanced multi-signal strategy

## Notes

- Cambrian data is real-time (30s cache)
- API rate limit: 600 req/min
- Focus on SOL initially (known to work)
- Expand to other majors after validation
