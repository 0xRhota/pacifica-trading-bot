# Hibachi Order Execution - Implementation Status

**Date**: November 24, 2025
**Status**: ✅ 100% COMPLETE - All Systems Operational

## ✅ RESOLUTION (November 24, 2025)

**Issue**: Signature verification was failing with `MacError for payload`

**Root Cause**: Max fees encoding used `× 10^6` instead of `× 10^8`

**Solution**: Examined official Hibachi Python SDK source code (https://github.com/hibachi-xyz/hibachi_sdk) and discovered the correct encoding:
```python
# WRONG (our old code)
max_fees_int = int(0.005 * (10 ** 6))  # = 5000

# CORRECT (from official SDK)
max_fees_int = int(0.005 * (10 ** 8))  # = 500000
```

**Test Results**:
- ✅ Order ID: `592174964486177792`
- ✅ Opened $2.00 SOL/USDT-P LONG position
- ✅ Entry price: $136.8737538
- ✅ Position closed successfully
- ✅ Signature verification working perfectly

---

## What Works ✅

### Read Operations (GET)
- ✅ Get markets
- ✅ Get balance ($58.08 USDT confirmed)
- ✅ Get positions
- ✅ Get orders
- ✅ Get price data
- ✅ Get orderbook data

**Authentication**: Simple `Authorization` header with API key

### Write Operations (POST/DELETE) - API Format Discovered

Through iterative testing, we've discovered the correct request format for orders:

```json
{
  "accountId": 22919,           // Integer, not string
  "symbol": "SOL/USDT-P",
  "side": "BID",                // BID = buy, ASK = sell (not BUY/SELL)
  "orderType": "MARKET",        // Not "type"
  "quantity": "0.01457682",
  "nonce": 1732476394728,       // Millisecond timestamp
  "maxFeesPercent": "0.00500000" // Required field, 0.045%-1.0% range
}
```

## What's Pending ⚠️

### Binary Buffer Signature - Verification Failing

**Current Error**: `"Invalid signature: Failed to verify signature: MacError for payload"`

**What We've Implemented Correctly** (per API docs):
1. ✅ Binary buffer structure (32 bytes for market orders):
   - Nonce: 8 bytes (millisecond timestamp, big-endian)
   - Contract ID: 4 bytes (3 for SOL/USDT-P)
   - Quantity: 8 bytes (amount × 10^underlyingDecimals)
   - Side: 4 bytes (1 for BID/buy, 0 for ASK/sell)
   - Max Fees: 8 bytes (0.005 × 10^6 = 5000 per docs)
2. ✅ Price field omitted for market orders
3. ✅ HMAC-SHA256 signature with API secret
4. ✅ Signature included in JSON request body

**What's Unknown / Needs Investigation**:
- API secret encoding (tried both base64-decoded and raw string)
- Exact max_fees calculation (docs show × 10^8 but example suggests × 10^6)
- Possible endianness issues
- API might need different signature input format

**API consistently returns**: Buffer payload is being read correctly by server (verified from error messages), but signature verification fails

**Official Docs**: https://api-doc.hibachi.xyz/

## Key Discoveries

### 1. Account ID Format
- ✅ Must be integer in request body: `"accountId": 22919`
- ❌ Not as string: `"accountId": "22919"`
- ❌ Not as query parameter

### 2. Order Side Values
- ✅ Use `"BID"` for buy orders
- ✅ Use `"ASK"` for sell orders
- ❌ Not "BUY" or "SELL"

### 3. Required Fields
- `accountId` (integer)
- `symbol` (string)
- `side` ("BID" or "ASK")
- `orderType` (not "type")
- `quantity` (string)
- `nonce` (integer timestamp)
- `maxFeesPercent` (string, 0.00045-1.0 range)

### 4. API Secret Encoding
- Keys are base64-encoded in .env
- Must decode before using in HMAC:
  ```python
  self.api_secret_bytes = base64.b64decode(api_secret)
  ```

## Next Steps

### Recommended: Contact Hibachi Support
The implementation follows the documented API specification, but signature verification is consistently failing. Request clarification on:

**Support Contact Information**:
- Account ID: 22919
- API Key: j5yVYdB3... (first 10 chars)
- Current implementation: Binary buffer signing per docs

**Questions for Support**:
1. API secret format: Should it be base64-decoded before HMAC signing, or used as-is?
2. Max fees encoding: Documentation says × 10^8, but example shows × 10^6. Which is correct?
3. Example request: Can you provide a complete working Python example for exchange-managed accounts?
4. Signature verification: What exactly is being signed? Is there any preprocessing of the buffer?

### Alternative Options

#### Option 1: Check for Official SDK
- Python SDK: https://github.com/hibachi-xyz/
- TypeScript examples: https://github.com/hibachi-xyz/hibachi-example-js
- Community implementations

#### Option 2: Use WebSocket API
- May have different/simpler authentication
- Could be easier to debug

#### Option 3: Testnet First
- If Hibachi offers testnet, test signature there first
- Less risk while debugging

## Test Script

**Location**: `scripts/hibachi/test_hibachi_order.py`

**Usage**:
```bash
# Dry run (preview only)
python3 scripts/hibachi/test_hibachi_order.py

# Execute order (when signatures work)
python3 scripts/hibachi/test_hibachi_order.py --confirm
```

## SDK Status

**File**: `dexes/hibachi/hibachi_sdk.py`

**What's Implemented**:
- Base64 secret decoding ✅
- Correct request body format ✅
- HMAC-SHA256 signature generation ✅
- Pre-serialized JSON for signature matching ✅

**What Needs Fixing**:
- Signature header configuration (1-2 line fix once we know the header names)

## Summary

We're **one configuration detail away** from working order execution. Everything else is implemented correctly:
- API format discovered through testing
- Request body structure correct
- HMAC signing logic implemented
- Just need correct header names from official docs

**Estimated Effort to Complete**: 5-10 minutes once header names confirmed

---

**Files**:
- SDK: `dexes/hibachi/hibachi_sdk.py`
- Test: `scripts/hibachi/test_hibachi_order.py`
- Docs: `research/hibachi/API_REFERENCE.md`
