# Lighter Adapter Debugging Guide

## Problem
The new unified Lighter adapter (`dexes/lighter/adapter.py`) returns `None` for all `get_market_data()` calls, while the old bot (`lighter_agent/`) works fine.

## Debug Logging Added

I've added comprehensive debug logging to `dexes/lighter/adapter.py` to diagnose the issue:

### 1. Market Initialization Logging
When `_fetch_markets()` is called:
```
✅ Fetched {N} markets from Lighter exchange
   Active markets: {N}
   Known symbol mappings:
     BTC: market_id={id} status={status}
     SOL: market_id={id} status={status}
     ETH: market_id={id} status={status}
     PENGU: market_id={id} status={status}
     XPL: market_id={id} status={status}
     ASTER: market_id={id} status={status}
```

**What to check**:
- Are the market_ids the same as the old bot hardcoded IDs (BTC=1, SOL=2, ETH=3, etc.)?
- Are all symbols found? If not, which ones are missing?
- Are they all status="active"?

### 2. get_market_data() Call Logging
For each `get_market_data(symbol)` call:

**If market_id not found**:
```
❌ No market_id found for symbol {symbol}
   Available mappings: {dict}
```

**If SDK not initialized**:
```
❌ SDK not initialized or missing api_client for {symbol}
```

**When fetching data**:
```
📊 Fetching market data for {symbol} (market_id={id})
   Calling candlestick_api.candlesticks(market_id={id}, resolution={res}, count_back={limit})
   Result: {result_object}
```

**If no data returned**:
```
❌ No candlestick data returned for {symbol} (market_id={id})
   Result object: {result}
```

**On success**:
```
✅ Successfully fetched market data for {symbol}: price={price}, candles={count}, indicators=[...]
```

**On exception**:
```
❌ Error fetching market data for {symbol} (market_id={id}): {exception_type}: {message}
   Traceback: {full_traceback}
```

## How to Debug

### Step 1: Restart Lighter Bot with Debug Logging
```bash
# Stop old bot
pkill -f "lighter_bot"

# Start with debug logging (set logging level to DEBUG)
# Option A: Modify bots/lighter_bot.py to set logging.DEBUG
# Option B: Run with environment variable
PYTHONUNBUFFERED=1 python3 bots/lighter_bot.py 2>&1 | tee logs/lighter_debug.log
```

### Step 2: Check Startup Logs
Look for the "Known symbol mappings" section:
```bash
grep -A 10 "Known symbol mappings" logs/lighter_debug.log
```

**Expected**:
- All 6 symbols (BTC, SOL, ETH, PENGU, XPL, ASTER) should have market_ids
- All should be status="active"

**If different market_ids**:
- The old bot used hardcoded IDs (BTC=1, SOL=2, etc.)
- The new adapter fetches dynamically from exchange
- Market IDs may have changed on Lighter exchange

### Step 3: Check get_market_data() Logs
```bash
grep "Fetching market data" logs/lighter_debug.log
```

**Look for**:
1. Which symbols are being fetched?
2. What are the market_ids?
3. Are there any "No market_id found" errors?
4. Are there any "No candlestick data returned" warnings?

### Step 4: Check for Exceptions
```bash
grep -A 5 "❌ Error fetching" logs/lighter_debug.log
```

**This will show**:
- Full exception type and message
- Complete traceback
- Exact line where it failed

## Likely Issues

### Issue 1: Market IDs Changed
**Old bot hardcoded**:
```python
MARKET_IDS = {'BTC': 1, 'SOL': 2, 'ETH': 3, 'PENGU': 4, 'XPL': 5, 'ASTER': 6}
```

**New adapter fetches dynamically from exchange**.

**If market IDs changed**:
- The old bot's hardcoded IDs might be wrong
- The new adapter's dynamic IDs are correct
- But the Lighter API might reject certain market_ids

**Solution**: Compare logged market_ids with old hardcoded ones.

### Issue 2: API Client Initialization
The old bot initializes CandlestickApi differently:
```python
# Old bot
self.candlestick_api = lighter.CandlestickApi(self.lighter_sdk.api_client)

# New adapter
candlestick_api = lighter.CandlestickApi(self.sdk.api_client)
```

**Check**:
- Is `self.sdk.api_client` properly initialized?
- Is it the same Configuration as the old bot?

### Issue 3: Async/Await Pattern
The new adapter uses:
```python
result = await candlestick_api.candlesticks(...)
```

But the Lighter SDK might not be async. Check if it should be:
```python
# Run in executor
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, candlestick_api.candlesticks, ...)
```

**Already handled**: The adapter already does this for `order_books()`.

### Issue 4: Market Status Filtering
The old bot hardcodes 6 markets. The new adapter fetches ALL markets but only returns active ones:
```python
return [m['symbol'] for m in self._markets.values() if m['status'] == 'active']
```

**Check**: Are BTC, SOL, ETH, PENGU, XPL, ASTER all "active"?

## Expected Debug Output

### Good Startup:
```
✅ Fetched 100+ markets from Lighter exchange
   Active markets: 50
   Known symbol mappings:
     BTC: market_id=1 status=active
     SOL: market_id=2 status=active
     ETH: market_id=3 status=active
     PENGU: market_id=4 status=active
     XPL: market_id=5 status=active
     ASTER: market_id=6 status=active
```

### Good get_market_data():
```
📊 Fetching market data for BTC (market_id=1)
   Calling candlestick_api.candlesticks(market_id=1, resolution=15m, count_back=100)
   Result: <CandlestickResponse object>
✅ Successfully fetched market data for BTC: price=95234.50, candles=100, indicators=['rsi', 'macd', ...]
```

### Bad get_market_data() - No Market ID:
```
❌ No market_id found for symbol BTC
   Available mappings: {'BTCUSD': 1, ...}
```
**Cause**: Symbol name mismatch (exchange uses "BTCUSD" not "BTC")

### Bad get_market_data() - No Data:
```
📊 Fetching market data for BTC (market_id=1)
   Calling candlestick_api.candlesticks(market_id=1, resolution=15m, count_back=100)
   Result: None
❌ No candlestick data returned for BTC (market_id=1)
   Result object: None
```
**Cause**: API returned None (possible authentication issue, rate limit, or market_id invalid)

### Bad get_market_data() - Exception:
```
📊 Fetching market data for BTC (market_id=1)
❌ Error fetching market data for BTC (market_id=1): ApiException: Forbidden
   Traceback: ...
```
**Cause**: API authentication failure, permission issue, or invalid parameters

## Next Steps

1. **Run the bot with debug logging enabled**
2. **Check the startup logs** for market ID mappings
3. **Check get_market_data() logs** for each symbol
4. **If you see errors, paste them** and I'll provide the fix

## Quick Test Script

To test outside the bot:
```python
import asyncio
from dexes.lighter.adapter import LighterAdapter
import os

async def test():
    adapter = LighterAdapter(
        api_key_private=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        api_key_public=os.getenv("LIGHTER_API_KEY_PUBLIC"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX"))
    )

    await adapter.initialize()

    # Test BTC
    data = await adapter.get_market_data("BTC")
    print(f"BTC data: {data}")

asyncio.run(test())
```

---

**Status**: Debug logging added to `dexes/lighter/adapter.py`
**Next**: Restart Lighter bot and check logs
**File**: `/Users/admin/Documents/Projects/pacifica-trading-bot/LIGHTER_DEBUG_GUIDE.md`
