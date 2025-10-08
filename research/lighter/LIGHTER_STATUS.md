# Lighter Integration Status - Work in Progress

**Date**: 2025-10-07 00:24 UTC
**Status**: SDK has significant bugs, working on workarounds

---

## What's Working ✅

1. **Connection**: Can connect to Lighter mainnet successfully
2. **Authentication**: API key is registered and validated (account #126039)
3. **Account Balance**: Can fetch account info - you have **$433.76** available
4. **Market Data**: Can list all 91 available markets
5. **SOL Market**: Identified - market_id=2, min size 0.050 SOL

---

## SDK Issues Discovered ❌

### Issue 1: Wrapper Bug
The SDK's `@tx_decorator` wrapper has a critical bug:
```python
# Line 98 in signer_client.py
if ret.code != CODE_OK:  # Fails when ret is None
    AttributeError: 'NoneType' object has no attribute 'code'
```

**Impact**: All high-level order methods (`create_order`, `create_market_order`) fail immediately

### Issue 2: Market Order Price Validation
**Error**: `"OrderPrice should not be less than 1"`

**Finding**: Lighter requires `price > 0` even for market orders with IOC time-in-force
- Cannot use `price=0` like most exchanges
- Must specify a limit price even for "market" orders
- IOC flag makes it behave like a market order

### Issue 3: Order Expiry Validation
**Error**: `"OrderExpiry is invalid"`

**Finding**: The SDK's `sign_create_order` method fails to calculate valid expiry timestamps
- Tried manual expiry (current_time + 86400) - failed
- Tried default (-1) - failed
- Limit orders with POST_ONLY hang during signing

---

## Technical Details

### Lighter vs Pacifica Differences
| Feature | Pacifica | Lighter |
|---------|----------|---------|
| Blockchain | Solana | zkSync (ETH L2) |
| SDK Style | Sync | Async |
| Market Orders | price=0 | price > 0 required |
| Order Size | Float | Integer (with decimals) |
| Min SOL Order | Any | 0.050 SOL ($11-12) |

### SOL Market Specs
```
Symbol: SOL
Market ID: 2
Min Base: 0.050 SOL
Min Quote: $10 USD
Price Decimals: 3 (e.g., 230.500)
Size Decimals: 3 (e.g., 0.050)
```

### Your Account
```
Account Index: 126039
Balance: $433.76
Available Markets: 91 (including SOL, BTC, ETH, PENGU, XPL, ASTER)
Existing Positions: PENGU, XPL, ASTER (all $0)
```

---

## Attempts Made

### Attempt 1: High-Level SDK Methods
```python
await client.create_market_order(...)
```
**Result**: SDK wrapper bug - returns None instead of TxHash

### Attempt 2: Direct Transaction Construction
```python
tx = CreateOrder()
tx.market_index = 2
await client.send_tx(tx)
```
**Result**: Unsigned transaction rejected - "api key not found"

### Attempt 3: Sign + Send
```python
signed_tx = client.sign_create_order(...)
await client.send_tx(signed_tx)
```
**Result**: Multiple validation errors:
- Price validation (fixed by using price > 0)
- Expiry validation (still failing)
- Signing hangs with certain parameters

---

## Next Steps

### Option A: Fix SDK Issues (Complex)
1. Fork lighter-python SDK
2. Fix wrapper decorator bug
3. Fix expiry calculation
4. Submit PR to upstream

**Time**: Several hours
**Risk**: High - SDK internals are complex

### Option B: Use Raw HTTP API (Bypasses SDK)
1. Study Lighter's REST API directly
2. Manually construct and sign requests
3. Use `requests` or `aiohttp` to call API
4. Bypass buggy SDK entirely

**Time**: 2-3 hours
**Risk**: Medium - requires understanding signing

### Option C: Wait for SDK Fix
1. Report bugs to Lighter team
2. Wait for official fix
3. Implement once SDK is stable

**Time**: Unknown (days/weeks)
**Risk**: Low but slow

### Option D: Try Lighter UI for Manual Test (Fastest)
1. Go to https://app.lighter.xyz
2. Connect wallet (account #126039)
3. Manually place small SOL order
4. Verify it works
5. Then tackle SDK/API integration

**Time**: 5 minutes
**Risk**: None - just testing

---

## Recommendation

**For tonight (you're going to sleep)**:
1. Manually test an order via Lighter UI to confirm the account works
2. This eliminates account/funding as the issue
3. Proves the integration is possible

**Tomorrow**:
1. If manual order works → pursue Option B (raw API)
2. If manual order fails → investigate account setup
3. Meanwhile, run Pacifica bot as-is (it's working fine)

---

## Files Created

- `get_markets.py` - Lists all 91 Lighter markets ✅
- `place_sol_order.py` - Attempted order with SDK (buggy)
- `buy_sol_manual.py` - Manual transaction construction (validation errors)
- `quick_buy.py` - Simple test (SDK bugs)
- `test_lighter_order.py` - Order test scaffold

---

## Key Learnings

1. **Lighter SDK is unstable** - multiple critical bugs
2. **Account is funded** - $433.76 available
3. **Connection works** - can query markets, account data
4. **Raw API approach needed** - SDK can't be trusted
5. **Manual UI test recommended** - quickest validation

---

## When You Wake Up

Check this file for status. If you want to proceed:

1. **Quick test** (5 min):
   ```
   Go to https://app.lighter.xyz
   Place tiny SOL order manually
   Confirm it works
   ```

2. **Continue integration** (if manual works):
   ```
   I'll implement raw HTTP API approach
   Bypass SDK entirely
   Build reliable order placement
   ```

3. **Or**: Focus on Pacifica bot improvements while Lighter SDK matures

**Pacifica bot is running fine** - made trades while you were afk, currently has 1 SOL position open.
