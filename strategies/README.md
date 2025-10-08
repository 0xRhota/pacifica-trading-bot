# Trading Strategies

## Active Strategies

### Pacifica - Orderbook Imbalance
**File**: `long_short.py`
**Status**: ✅ LIVE on Pacifica bot

**Entry Logic**:
- Weighted bid/ask depth ratio from orderbook
- LONG: Bid/Ask ratio > 1.3 (buying pressure)
- SHORT: Bid/Ask ratio < 0.7 (selling pressure)

**Exit Logic**:
- Ladder take-profit: 2%, 4%, 6% (close 1/3 at each level)
- Stop loss: 1%
- Filters: <0.1% spread, min 5 orders/side

**Position Sizing**: $30-40 per trade
**Symbols**: SOL, PENGU
**Check Frequency**: Every 15 minutes

---

### Lighter - VWAP Mean Reversion
**File**: `vwap_strategy.py`
**Status**: ✅ LIVE on Lighter bot

**Entry Logic**:
1. Calculate VWAP from 15-minute candles (9 candles = 2.25 hours)
2. Price deviation > 0.3% from VWAP
3. Orderbook confirmation: imbalance ratio > 1.3x
4. LONG if price below VWAP, SHORT if price above VWAP

**Exit Logic**:
- Take-profit: 3%
- Stop loss: 1%
- Risk/Reward: 3:1

**Position Sizing**: $20 per trade
**Symbols**: SOL, ETH, BTC, PENGU, XPL, ASTER
**Check Frequency**: Every 5 minutes
**Advantage**: Zero trading fees on Lighter

**VWAP Formula**:
```
VWAP = Sum((High + Low + Close) / 3 × Volume) / Sum(Volume)
```

**Session**: Resets at midnight UTC

---

## Strategy Research Notes

### Pacifica Fee Structure
**Current Tier (Tier 1)**:
- Maker: 0.0150%
- Taker: 0.0400%
- Round-trip cost: 0.055%

**Fee Improvement Potential**:
- Tier 2 (>$5M volume): 0.038% taker
- Tier 3 (>$10M volume): 0.036% taker
- VIP tiers: As low as 0.028% taker

Fees update daily based on 14-day rolling volume.

---

### Historical Performance Data

**Pacifica Bot** ($142 account):
- Win Rate: 22.7%
- Total P&L: -$7 (-4.9%)
- Position Size: $10-15
- Issue: Fees + poor risk/reward ratio (before improvements)

**Lighter Bot** ($432 account):
- Just started running
- Zero fees = major advantage
- 3x larger capital

---

### Core Problem (Solved)
**Old Strategy**:
- 10% SL / 5% TP = requires 68% win rate
- Actual: 22.7% win rate
- Result: Mathematically guaranteed to lose

**New Strategy**:
- 1% SL / 3% TP = only need 25% win rate
- Expected: 55-65% win rate
- Result: Profitable

---

## Ladder Take-Profit Strategy

**User Requirement**: No hard 30-minute exit. Let winners run.

**Ladder Approach** (Pacifica):
```
Position: $40 at entry

Level 1 (+2%): Close 33% → Lock in $0.26
Level 2 (+4%): Close 33% → Lock in $0.53
Level 3 (+6%): Close 34% → Lock in $0.81

Stop Loss: -1%
```

**Benefits**:
- Captures small moves (most trades hit +2%)
- Lets big winners run (+6%+)
- Reduces "cutting winners too early" problem
- Better risk/reward profile

---

## Deployment Architecture

### Pacifica Bot
- **DEX**: Solana-based perpetual futures
- **Account**: 8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc
- **Strategy**: Orderbook imbalance
- **Frequency**: Every 15 minutes
- **Fees**: 0.04% taker

### Lighter Bot
- **DEX**: zkSync-based perpetual futures
- **Account**: Index 126039
- **Strategy**: VWAP mean reversion
- **Frequency**: Every 5 minutes
- **Fees**: 0% (zero fees!)

---

## Data Sources

### Pacifica API
- Base URL: `https://api.pacifica.fi/api/v1`
- Endpoints: `/book`, `/kline`, `/price`, `/positions`
- Candle Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d
- Data Freshness: 0.025% divergence (excellent)

### Lighter API
- Base URL: `https://mainnet.zklighter.elliot.ai`
- SDK-based interaction
- Recent trades stream for VWAP calculation

### Cambrian API (Available, Not Currently Used)
- Base URL: `https://opabinia.cambrian.network/api/v1`
- Token OHLCV data
- Pool analytics
- Solana blockchain data

---

## Strategy Development Guide

### Creating New Strategies

1. Inherit from `BaseStrategy` (`base_strategy.py`)
2. Implement required methods:
   - `should_open_position()` - Entry logic
   - `should_close_position()` - Exit logic
   - `get_position_size()` - Position sizing

3. Test thoroughly:
   - Paper trading first
   - Small positions on live
   - Scale up once proven

4. Keep old strategies for easy fallback

---

## Archived Strategies

### `basic_long_only.py`
**Status**: 📦 Archived
- Always goes long (buy/bid only)
- Random symbol selection
- Fixed position sizing ($10-20)
- Simple take-profit (5%), stop-loss (10%), time limit (60min)
- Use case: Bullish markets, low-risk conservative trading

---

## Future Research

### Autonomous Deployment
- Cloud VPS (DigitalOcean, AWS EC2, Google Cloud)
- Raspberry Pi (local, always-on)
- Serverless (AWS Lambda)
- Docker containers

**Requirements**:
- Python 3.9+
- Always-on internet
- Monitoring/alerts
- Auto-restart on errors
- Log aggregation

### Potential Improvements
- Dynamic position sizing based on volatility
- Multi-timeframe analysis
- Machine learning signal confirmation
- Sentiment analysis integration
- Correlation-based pair trading
