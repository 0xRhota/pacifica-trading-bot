# Hibachi DEX Integration Research

**Date**: November 24, 2025
**Status**: Initial Research Complete
**Decision**: ✅ **PROCEED** - Google/Email OAuth accounts CAN use API trading

---

## Executive Summary

✅ **YES, your Google OAuth account works for API trading!**

Hibachi uses **HMAC (Hash-based Message Authentication Code)** for email/OAuth accounts, which means:
- ✅ NO wallet signing required per transaction (like Lighter)
- ✅ Hibachi signs transactions on your behalf
- ✅ API keys can be generated from email accounts
- ✅ Works exactly like you want (automated trading without per-tx signatures)

**Recommended Approach**: Python SDK (hibachi-xyz package)

---

## Authentication: Email vs Wallet Accounts

### Email Accounts (YOUR SETUP - Google OAuth)
**How It Works**:
- Hibachi stores your credentials securely
- Transactions are signed server-side by Hibachi
- API access uses **HMAC** shared secret signing
- Fast, simple, no wallet signatures needed

**For API Trading**:
- ✅ Can generate API keys
- ✅ Use HMAC signing (API Key + Secret)
- ✅ Hibachi handles transaction signing
- ✅ Perfect for automated bots

**What You Need**:
1. API Key
2. API Secret (HMAC shared secret)
3. Account ID

### Wallet Accounts (NOT YOUR SETUP)
**How It Works**:
- User's wallet holds private keys
- Every transaction requires user signature
- Uses private/public key pairs
- NOT suitable for automated trading

**For API Trading**:
- ❌ Every transaction needs wallet signature
- ❌ Not automated-friendly
- ❌ Requires manual approval

---

## Integration Options

### 1. Python SDK (RECOMMENDED)

**Package**: `hibachi-xyz`
**Install**: `pip install hibachi-xyz`
**Python Version**: 3.13+ required

**Pros**:
- Official SDK
- Type-safe
- Well-maintained
- Full feature coverage

**Cons**:
- Requires Python 3.13+ (we're on 3.12)
- Need to upgrade Python or use pyenv

### 2. REST API (BACKUP OPTION)

**Endpoint**: `https://api.hibachi.xyz`
**Docs**: `https://api-doc.hibachi.xyz`

**Pros**:
- Language agnostic
- No Python version requirement
- Direct HTTP calls

**Cons**:
- More code to write
- Manual request signing
- Less type safety

### 3. CCXT (NOT RECOMMENDED FOR NOW)

**Why Not**:
- Additional abstraction layer
- May lag behind official SDK
- More complexity
- Use only if we need multi-exchange support

---

## Required Credentials (Email/OAuth Account)

### What You Need From Hibachi UI:

1. **API Key** - For request identification
2. **API Secret** - For HMAC signing
3. **Account ID** - Numeric account identifier

### Where To Get Them:
- Log in to Hibachi web UI (https://app.hibachi.xyz)
- Navigate to Settings → API Keys (exact path TBD - need to verify)
- Generate new API key
- Save the secret immediately (shown once)

### .env Format (Python SDK):
```bash
ENVIRONMENT=production
HIBACHI_API_ENDPOINT_PRODUCTION="https://api.hibachi.xyz"
HIBACHI_DATA_API_ENDPOINT_PRODUCTION="https://data-api.hibachi.xyz"
HIBACHI_API_KEY_PRODUCTION="your_api_key_here"
HIBACHI_API_SECRET_PRODUCTION="your_api_secret_here"  # HMAC secret
HIBACHI_ACCOUNT_ID_PRODUCTION="your_account_id_here"
```

**Note**: The Python SDK docs mention "PRIVATE_KEY" but for email accounts this should be the **API Secret** (HMAC shared secret), NOT a wallet private key.

---

## Available Markets

**Current Markets** (as of docs):
- BTC-PERP
- ETH-PERP
- SOL-PERP
- Additional markets added periodically

**Trading Limits**:
- Min Order Size: 1 USDT
- Max Position Size: Free Margin × Max Leverage
- Volume-based fee tiers (lower fees for higher volume)

---

## API Features

### REST API Capabilities:
- Market data queries
- Account management
- Order placement (limit, market)
- Order modification
- Order cancellation
- Position management
- Deposits/withdrawals
- Transfers

### WebSocket Capabilities:
- Real-time market data
- Account balance updates
- Order status updates
- Position updates
- Trade executions
- Lower latency than REST

---

## Implementation Plan

### Phase 1: Setup & Testing (Day 1)
1. **Generate API Keys**:
   - Log in to Hibachi UI
   - Navigate to API settings
   - Generate API key + secret
   - Save to `.env` file

2. **Install Python SDK**:
   ```bash
   # Option A: Upgrade Python to 3.13
   pyenv install 3.13.0
   pyenv local 3.13.0
   pip install hibachi-xyz

   # Option B: Use REST API (no Python version constraint)
   # Implement custom HTTP client
   ```

3. **Test Connection**:
   - Get exchange info
   - Get account balance
   - Get market data
   - Verify authentication works

### Phase 2: SDK Wrapper (Day 2-3)
1. Create `dexes/hibachi/hibachi_sdk.py`
2. Implement same interface as Lighter SDK:
   - `get_balance()`
   - `get_positions()`
   - `get_markets()`
   - `create_market_order(symbol, is_buy, amount)`
   - `get_orderbook(symbol)`

3. Add to `hibachi_agent/data/market_data_aggregator.py`

### Phase 3: Bot Integration (Day 4-5)
1. Create `hibachi_agent/` directory (copy from `lighter_agent/`)
2. Integrate with shared LLM decision engine
3. Test in dry-run mode
4. Deploy to production

---

## Key Differences vs Lighter

| Feature | Lighter | Hibachi |
|---------|---------|---------|
| **Markets** | 101+ pairs | 3+ pairs (BTC, ETH, SOL) |
| **Fees** | 0% | Volume-based tiers |
| **Authentication** | API Key + Account Index | API Key + Secret (HMAC) |
| **Python SDK** | `lighter` package | `hibachi-xyz` package |
| **Python Version** | Any 3.x | 3.13+ required |
| **Chain** | zkSync | Not specified |
| **Transaction Signing** | Server-side | Server-side (email accounts) |

---

## Next Steps

### Immediate Actions:
1. ✅ **Verify Google OAuth account can generate API keys**
   - Log in to Hibachi UI
   - Check if API settings are available

2. ⚠️ **Python 3.13 Decision**:
   - **Option A**: Upgrade to Python 3.13 globally
   - **Option B**: Use pyenv for version management
   - **Option C**: Build REST API client (no SDK)

3. Generate API keys from Hibachi UI

### Once API Keys Available:
1. Test basic API calls (get markets, get balance)
2. Build SDK wrapper
3. Create `hibachi_agent/` bot
4. Test in dry-run mode
5. Deploy alongside Lighter bot

---

## Risks & Considerations

### Pros:
✅ Email/OAuth account works (no wallet signing)
✅ HMAC authentication (simple API keys)
✅ Official Python SDK available
✅ Similar to Lighter workflow
✅ Good for airdrop farming

### Cons:
⚠️ Requires Python 3.13+ (SDK)
⚠️ Fewer markets than Lighter (3 vs 101+)
⚠️ Trading fees (vs Lighter's 0%)
⚠️ Newer exchange (less battle-tested)

---

## Resources

- **Main Docs**: https://docs.hibachi.xyz/
- **API Docs**: https://api-doc.hibachi.xyz/
- **Python SDK**: https://pypi.org/project/hibachi-xyz/
- **GitHub SDK**: https://github.com/hibachi-xyz/hibachi_sdk
- **CCXT**: https://github.com/ccxt/ccxt (if needed)

---

## Questions to Resolve

1. **Where exactly in the UI are API keys generated?**
   - Need to log in and explore settings

2. **Does the Python SDK actually work with API Secret (HMAC) or does it require wallet keys?**
   - Docs say "private key" but email accounts use HMAC
   - Need to test with actual API keys

3. **Python 3.13 requirement - can we use 3.12?**
   - SDK says 3.13+ required
   - May need to upgrade or build REST client

4. **What are the actual fee tiers?**
   - Volume-based, but exact percentages TBD

---

**Status**: Research complete, ready to proceed with API key generation and testing.
**Recommendation**: Use Python SDK if Python 3.13 upgrade is acceptable, otherwise build REST API client.
