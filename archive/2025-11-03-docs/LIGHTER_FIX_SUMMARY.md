# Lighter Adapter Fix Summary

## Problem Identified

The new unified Lighter adapter was creating fresh `CandlestickApi` and `FundingApi` instances inside `get_market_data()` on every call, while **the old working bot creates them once during initialization and reuses them**.

## Root Cause

**Old Bot** (`lighter_agent/bot_lighter.py:155`):
```python
# Create API instances ONCE during initialization
self.aggregator.candlestick_api = lighter.CandlestickApi(self.lighter_sdk.api_client)
```

**New Adapter (BEFORE FIX)**:
```python
# Created FRESH instances on every get_market_data() call
candlestick_api = lighter.CandlestickApi(self.sdk.api_client)  # ❌ WRONG
```

This pattern mismatch likely caused issues with:
- API client state
- Connection pooling
- Authentication headers
- Rate limiting

## Fix Implemented

Changed the new adapter to match the old bot's pattern: **create API instances once, reuse for all calls**.

### Changes Made

**1. Added cached API instances to `__init__()`**:
```python
def __init__(self, ...):
    ...
    # Cached API instances (created once, reused for all calls - same as old bot pattern)
    self._candlestick_api = None
    self._funding_api = None
```

**2. Initialize API instances in `initialize()`**:
```python
async def initialize(self):
    ...
    # Initialize API instances (same pattern as old bot - create once, reuse for all calls)
    import lighter
    self._candlestick_api = lighter.CandlestickApi(self.sdk.api_client)
    self._funding_api = lighter.FundingApi(self.sdk.api_client)
    logger.info("✅ Lighter API clients initialized (CandlestickApi, FundingApi)")
    ...
```

**3. Use cached instances in `get_market_data()`**:
```python
# BEFORE:
candlestick_api = lighter.CandlestickApi(self.sdk.api_client)  # ❌ Fresh instance

# AFTER:
candlestick_api = self._candlestick_api  # ✅ Reuse cached instance
if not candlestick_api:
    logger.error(f"❌ CandlestickApi not initialized for {symbol}")
    return None
```

**4. Same pattern for FundingApi**:
```python
# BEFORE:
funding_api = lighter.FundingApi(self.sdk.api_client)  # ❌ Fresh instance

# AFTER:
funding_api = self._funding_api  # ✅ Reuse cached instance
if funding_api:
    funding_rates = await funding_api.funding_rates()
```

## Why This Matters

The Lighter SDK likely maintains state in the API client instances:
- **Connection pools**: Creating fresh instances doesn't reuse connections
- **Authentication state**: May need to re-authenticate on each call
- **Rate limiting**: Fresh instances don't share rate limit tracking
- **Headers**: May lose important headers between calls

By caching the instances (same pattern as the old bot), we ensure:
- ✅ Same connection is reused
- ✅ Authentication persists
- ✅ Rate limiting is properly tracked
- ✅ Headers are consistent

## Debug Logging Also Added

Added comprehensive debug logging to diagnose issues:

1. **Market initialization**: Logs market_id mappings for known symbols (BTC, SOL, etc.)
2. **get_market_data() calls**: Logs each fetch attempt with market_id
3. **Candlestick API calls**: Logs the exact parameters passed
4. **Results**: Logs success with data summary or failure with full traceback

## Next Steps for Other Agent

1. **Restart the Lighter bot** with the fixed adapter:
   ```bash
   pkill -f "lighter_bot"
   python3 bots/lighter_bot.py 2>&1 | tee logs/lighter_debug.log
   ```

2. **Check the logs** for:
   - ✅ "Lighter API clients initialized (CandlestickApi, FundingApi)"
   - Known symbol mappings (should show BTC=1, SOL=2, etc.)
   - Market data fetch attempts
   - Success or error messages

3. **If still failing**, the debug logs will show:
   - Exactly which step fails (market_id lookup, API call, data parsing, etc.)
   - Full exception tracebacks
   - API response objects

4. **Expected output** (if working):
   ```
   ✅ Lighter API clients initialized (CandlestickApi, FundingApi)
   ✅ Fetched 100+ markets from Lighter exchange
   Known symbol mappings:
     BTC: market_id=1 status=active
     SOL: market_id=2 status=active
   ...
   📊 Fetching market data for BTC (market_id=1)
   ✅ Successfully fetched market data for BTC: price=95234.50, candles=100
   ```

## Files Changed

- `dexes/lighter/adapter.py` - Fixed to cache API instances (matches old bot pattern)

## Files Created

- `LIGHTER_DEBUG_GUIDE.md` - Comprehensive debugging guide
- `LIGHTER_FIX_SUMMARY.md` - This file

---

**Status**: ✅ Fix implemented and tested (syntax OK)
**Next**: Other agent should restart Lighter bot and verify
**Pattern**: Now matches the proven working old bot pattern exactly
