# Lighter Bot - Quick Start

## Ready to Test! ✅

Your Lighter integration is set up and ready. Here's how to test it:

---

## Step 1: Fund Your Account

1. Go to https://app.lighter.xyz
2. Connect your wallet (the one with ETH address `0xCe9784FcDaA99c64Eb88ef35b8F4A5EabDC129d7`)
3. Switch to sub-account **#126039**
4. Deposit USDC or other collateral
5. Verify balance shows in UI

**Recommended starting balance:** $50-100 USD for testing

---

## Step 2: Run Test Trade

```bash
python3 test_lighter_trade.py
```

This script will:
- Connect to your Lighter account
- Place a SMALL test order (default: 5 units on BTC-PERP)
- Show the position
- Log everything to `logs/lighter_*.log`

**Before running**, edit `test_lighter_trade.py` to set:
- `MARKET_INDEX` - Which market (0=BTC, 1=ETH, 2=SOL usually)
- `TEST_SIZE` - Size in base units (start SMALL like 5-10)
- `IS_BUY` - True for long, False for short

### The script will ask for confirmation before placing the order!

---

## Step 3: Monitor

**Check logs:**
```bash
tail -f logs/lighter_*.log
```

**Check position in UI:**
Go to https://app.lighter.xyz and view your positions

---

## Safety Features Built-In ✅

1. **Secure Logging**: All private keys auto-redacted from logs
2. **Separate Log Files**: Pacifica and Lighter logs kept separate
3. **Confirmation Prompt**: Script asks "yes" before placing order
4. **Small Test Size**: Default is very small to minimize risk

---

## Current Status

✅ Connection tested and working
✅ Account #126039 configured
✅ API keys registered
✅ Logging system ready
✅ Health checks operational

**Pacifica bot**: Still running (not affected)
**Lighter bot**: Ready for first test trade

---

## After Testing

Once you verify the test trade works:

1. Close the test position (manually in UI or let it run)
2. Decide if you want to:
   - **Option A**: Run separate Lighter bot alongside Pacifica
   - **Option B**: Refactor to multi-DEX architecture (cleaner long-term)

For Option A (quick), we can copy the Pacifica bot logic and adapt it for Lighter.
For Option B (proper), we implement the DEX adapter pattern from `research/MULTI_DEX_ARCHITECTURE.md`.

---

## Configuration Summary

```bash
# Your .env (current)
LIGHTER_API_KEY_PRIVATE=f4d86e54...
LIGHTER_API_KEY_PUBLIC=0x25c2a6a1...
LIGHTER_ACCOUNT_INDEX=126039  # The actual account number!
LIGHTER_API_KEY_INDEX=3
```

**Note**: ETH_PRIVATE_KEY already removed (only needed for registration)

---

## Quick Commands

```bash
# Test connection
python3 scripts/test_lighter_connection.py

# Check health of both DEXes
python3 utils/dex_health.py

# Run test trade (asks for confirmation)
python3 test_lighter_trade.py

# View logs
tail -f logs/lighter_*.log
tail -f logs/pacifica_*.log
```

---

## Need Help?

- **SDK Docs**: https://github.com/elliottech/lighter-python
- **API Docs**: https://apidocs.lighter.xyz
- **UI**: https://app.lighter.xyz
- **Your Account**: #126039 on zkSync mainnet

---

**Ready when you are!** Just fund the account and run `python3 test_lighter_trade.py`
