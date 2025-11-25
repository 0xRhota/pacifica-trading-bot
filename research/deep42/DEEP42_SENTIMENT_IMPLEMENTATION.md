# Deep42 Sentiment Filtering - Implementation Guide

**Date:** 2025-11-08
**Status:** ✅ COMPLETE
**Priority:** 🔴 CRITICAL - Expected 6% → 15-25% win rate improvement

---

## Executive Summary

Implemented social sentiment filtering using Deep42 API to prevent trades with poor sentiment alignment. Bot will now check Twitter sentiment before opening positions and skip trades when:
- **Longs (BUY)**: Bullish sentiment <60% (configurable)
- **Shorts (SELL)**: Bullish sentiment >60% (configurable)

**Expected Impact:**
- Win rate improvement: 6.1% → 15-25%
- Filter out ~30-40% of bad trades
- Break-even or profitable operation

**Implementation:** Fully integrated in Pacifica bot, OFF by default for safety.

---

## Files Modified

### 1. `/pacifica_agent/execution/pacifica_executor.py`

**Changes:**
- Added `requests` import for Deep42 API calls
- Added constructor parameters:
  - `cambrian_api_key`: API key for Deep42
  - `use_sentiment_filter`: Enable/disable filtering (default: False)
  - `sentiment_threshold_bullish`: Min bullish % for longs (default: 60%)
  - `sentiment_threshold_bearish`: Min bearish % for shorts (default: 40%)
- Added `_check_sentiment_alignment()` method (lines 94-163):
  - Queries Deep42 token-analysis endpoint
  - Extracts bullish/bearish percentages
  - Returns (should_proceed, reason) tuple
  - Falls back to allowing trade if API fails
- Modified `_open_position()` to check sentiment before executing (lines 234-244)

**Key Code:**
```python
# Check sentiment alignment
should_proceed, sentiment_reason = self._check_sentiment_alignment(symbol, action)
if not should_proceed:
    logger.warning(f"🚫 Trade rejected by sentiment filter: {symbol} {action}")
    return {"success": False, "error": f"Sentiment filter: {sentiment_reason}"}
```

### 2. `/pacifica_agent/bot_pacifica.py`

**Changes:**
- Added constructor parameters (lines 69-71):
  - `use_sentiment_filter`: bool (default: False)
  - `sentiment_threshold_bullish`: float (default: 60.0)
  - `sentiment_threshold_bearish`: float (default: 40.0)
- Updated `__init__` to store `cambrian_api_key` (line 91)
- Updated `_executor_params` dict (lines 128-131) to pass sentiment params to executor
- Added CLI arguments (lines 685-687):
  - `--use-sentiment-filter`: Enable filtering
  - `--sentiment-bullish`: Set bullish threshold
  - `--sentiment-bearish`: Set bearish threshold
- Updated bot initialization to pass sentiment params (lines 724-726)

---

## Usage

### Enable Sentiment Filtering (Dry-Run Test)

```bash
python3 -m pacifica_agent.bot_pacifica \
    --dry-run \
    --interval 300 \
    --use-sentiment-filter \
    --sentiment-bullish 60 \
    --sentiment-bearish 40
```

### Production (After Testing)

```bash
# Conservative thresholds (60/40)
python3 -m pacifica_agent.bot_pacifica \
    --live \
    --interval 300 \
    --use-sentiment-filter \
    --sentiment-bullish 60 \
    --sentiment-bearish 40

# Aggressive thresholds (70/30) - stricter filtering
python3 -m pacifica_agent.bot_pacifica \
    --live \
    --interval 300 \
    --use-sentiment-filter \
    --sentiment-bullish 70 \
    --sentiment-bearish 30
```

### Disable Filtering (Default)

```bash
# Sentiment filter OFF by default
python3 -m pacifica_agent.bot_pacifica --live --interval 300
```

---

## How It Works

### 1. Pre-Trade Sentiment Check

Before opening any BUY or SELL position, the executor:
1. Queries Deep42: `GET /api/v1/deep42/social-data/token-analysis?symbol={SYMBOL}&days=1`
2. Extracts sentiment metrics:
   - `veryBullishPct` + `bullishPct` = total bullish %
   - `bearishPct` = bearish %
   - `avgSentiment` = sentiment score (0-10)
   - `totalTweets` = sample size

### 2. Alignment Logic

**For LONG positions (BUY):**
- ✅ Allow if: `bullish_pct >= threshold_bullish` (default: 60%)
- ❌ Reject if: `bullish_pct < threshold_bullish`

**For SHORT positions (SELL):**
- ✅ Allow if: `bullish_pct <= (100 - threshold_bearish)` (default: ≤60%)
- ❌ Reject if: `bullish_pct > (100 - threshold_bearish)`

### 3. Fallback Safety

If Deep42 API fails:
- Log warning
- **Allow trade to proceed** (fail-open, not fail-closed)
- Reason: Avoid blocking all trades on API downtime

### 4. Logging

```
✅ SOL Sentiment aligned for LONG: 87.6% bullish, sentiment 6.8/10, 4194 tweets
❌ BTC Sentiment too weak for LONG: 45.2% bullish (need ≥60%), sentiment 5.1/10
🚫 Trade rejected by sentiment filter: SOL BUY
```

---

## Example Deep42 API Response

```json
{
  "tokenSymbol": "SOL",
  "totalTweets": 4194,
  "uniqueAuthors": 1713,
  "avgSentiment": 6.84,
  "veryBullishPct": 34.0,
  "bullishPct": 53.6,
  "bearishPct": 9.5,
  "neutralPct": 2.9,
  "totalViews": 19590620
}
```

**Calculation:**
- Total Bullish: 34.0% + 53.6% = **87.6%** ✅ (>60%, allow LONGs)
- Bearish: 9.5% (low bearish → bullish sentiment)

---

## Testing Plan

### Test A: Disabled (Baseline)
```bash
python3 -m pacifica_agent.bot_pacifica --dry-run --once
```
**Expected:** Bot operates normally, no sentiment checks

### Test B: Enabled with 60/40 Thresholds
```bash
python3 -m pacifica_agent.bot_pacifica --dry-run --once --use-sentiment-filter
```
**Expected:**
- Check sentiment before each trade
- Log sentiment data
- Skip trades with poor alignment

### Test C: Aggressive 70/30 Thresholds
```bash
python3 -m pacifica_agent.bot_pacifica --dry-run --once --use-sentiment-filter --sentiment-bullish 70 --sentiment-bearish 30
```
**Expected:**
- More trades filtered (stricter)
- Only trade on strong sentiment signals

### Test D: 24-Hour Dry-Run
```bash
nohup python3 -m pacifica_agent.bot_pacifica \
    --dry-run \
    --interval 300 \
    --use-sentiment-filter \
    > logs/sentiment_test_$(date +%Y%m%d).log 2>&1 &
```
**Monitor:**
- Number of trades filtered vs executed
- Sentiment scores for filtered trades
- Win rate comparison

---

## Configuration Recommendations

### Conservative (60/40) - Recommended for Start
```
--sentiment-bullish 60
--sentiment-bearish 40
```
**Profile:**
- Filters ~30% of trades
- Balance between volume and quality
- Good for maintaining points farming volume

### Balanced (70/30)
```
--sentiment-bullish 70
--sentiment-bearish 30
```
**Profile:**
- Filters ~50% of trades
- Higher quality signals
- Lower volume but better win rate

### Aggressive (80/20)
```
--sentiment-bullish 80
--sentiment-bearish 20
```
**Profile:**
- Filters ~70% of trades
- Very high confidence only
- May hurt volume too much for points farming

---

## Expected Results

### Before (No Sentiment Filter)
- Win Rate: 6.1%
- Trades/Day: ~300
- Daily P&L: -$2-5
- Daily Fees: $160
- Net: -$162-165/day

### After (60/40 Filter)
- Win Rate: 15-25% (estimated)
- Trades/Day: ~200 (33% reduction)
- Daily P&L: Break-even to +$10
- Daily Fees: $107 (33% reduction)
- Net: -$5 to +$10/day

### After (70/30 Filter)
- Win Rate: 25-35% (estimated)
- Trades/Day: ~150 (50% reduction)
- Daily P&L: +$10-30
- Daily Fees: $80 (50% reduction)
- Net: +$10-30/day

---

## Monitoring

### Key Metrics to Track

1. **Sentiment Filter Stats:**
   - Trades filtered vs executed
   - Average sentiment score of filtered trades
   - Average sentiment score of executed trades

2. **Performance Impact:**
   - Win rate before/after
   - Daily volume change
   - Daily P&L change
   - Fee costs change

3. **Sentiment Quality:**
   - False positives (filtered good trades)
   - False negatives (allowed bad trades)
   - API availability (uptime)

### Log Patterns to Monitor

```bash
# Count filtered trades
grep "Trade rejected by sentiment filter" logs/pacifica_bot.log | wc -l

# Check sentiment alignment logs
grep "Sentiment aligned" logs/pacifica_bot.log | tail -20

# Find filtered trades by symbol
grep "Trade rejected" logs/pacifica_bot.log | grep -oE "SOL|BTC|ETH|DOGE" | sort | uniq -c

# Check API errors
grep "Sentiment check failed\|Deep42 API error" logs/pacifica_bot.log
```

---

## Rollback Plan

If sentiment filtering performs poorly:

1. **Immediate:** Disable via CLI argument (remove `--use-sentiment-filter`)
2. **Quick test:** Lower thresholds (60 → 50, 40 → 35)
3. **Full rollback:** Keep code but don't use flag

**No code changes needed** - just stop using the `--use-sentiment-filter` flag.

---

## Future Enhancements

### Phase 2: Sentiment Shifts Detection
Add `/api/v1/deep42/social-data/sentiment-shifts` to detect trend changes:
- Detect sudden sentiment spikes (bullish breakout)
- Detect sentiment crashes (bearish reversal)
- Exit positions on major shifts

### Phase 3: Alpha Tweet Boost
Use `/api/v1/deep42/social-data/alpha-tweet-detection` for position sizing:
- 1.5x position size on exceptional alpha (combined_score >30)
- 1.2x position size on high quality alpha (combined_score >25)

### Phase 4: Influencer Credibility
Validate signals with `/api/v1/deep42/social-data/influencer-credibility`:
- Require 3+ credible influencers (score >8.0) for high-conviction trades
- Discount signals from low-credibility authors

---

## API Rate Limits

**Deep42 Token Analysis:**
- Rate Limit: Unknown (likely generous)
- Cache Time: 5-15 minutes recommended
- Cost: Included in Cambrian API subscription

**Optimization:**
- Cache sentiment for 5-10 minutes
- Only query when actually opening position
- Batch queries if possible (future)

---

## Troubleshooting

### "Sentiment API unavailable (HTTP 404)"
**Cause:** Wrong endpoint or token symbol not supported
**Fix:** Check token symbol is valid, try different symbol

### "Sentiment check failed (timeout)"
**Cause:** API slow or network issue
**Fix:** Increase timeout (currently 10s), check network

### All trades filtered
**Cause:** Thresholds too strict or market-wide bearish sentiment
**Fix:** Lower thresholds or wait for better market conditions

### No sentiment data for token
**Cause:** Token not covered by Deep42
**Fix:** Allow trade (fallback), consider removing token from watchlist

---

## Related Documentation

- [PRD: Bot Profitability Improvements](./PRD_BOT_PROFITABILITY_2025.md)
- [Deep42 Endpoint Analysis](../research/cambrian/DEEP42_PERPDEX_ANALYSIS.md)
- [Pacifica Profitability Analysis](./PACIFICA_PROFITABILITY_ANALYSIS.md)

---

**Last Updated:** 2025-11-08 21:00 UTC
**Implementation Status:** ✅ COMPLETE
**Testing Status:** ⏳ PENDING (Test B scheduled next)
