# Pacifica Trading Bot Setup

## Prerequisites

✅ Dependencies installed
✅ SDK integrated
⚠️ Need to configure `.env` file

## Step 1: Get Your Wallet Private Key

1. Open your Solana wallet (Phantom/Solflare)
2. Go to Settings → Security → Export Private Key
3. Copy the base58 private key (long string starting with a number)

## Step 2: Create .env File

Create a file named `.env` in the project root:

```bash
# Copy from .env.example
cp .env.example .env
```

Then edit `.env` and fill in:

```bash
SOLANA_PRIVATE_KEY=your_base58_private_key_here
PACIFICA_ACCOUNT_ADDRESS=YOUR_ACCOUNT_PUBKEY
```

**IMPORTANT:**
- `.env` is in `.gitignore` and will NOT be committed to git
- Keep this file secure - it contains your wallet private key
- Never share or commit this file

## Step 3: Test Live Order Placement

Run the test script to place a small $6 order:

```bash
python3 place_test_order.py
```

This will:
1. Show your account balance
2. Get current SOL price
3. Calculate a ~$6 position
4. Ask for confirmation
5. Place the order using SDK
6. Display the result

**You'll manually close this position in the Pacifica UI.**

## Step 4: Run Dry-Run Bot

The dry-run bot is already running! Check status:

```bash
./check_status.sh
```

Or view live logs:

```bash
tail -f dry_run.log
```

## Current Configuration

- **Check Frequency:** Every 45 seconds (checks if positions should close)
- **Trade Frequency:** Every 15 minutes (opens new positions)
- **Position Size:** $5-10 per trade
- **Max Leverage:** 5x
- **Strategy:** Longs only (bull market mode)
- **Mode:** DRY RUN (no real trades in dry_run_bot.py)

## Files Overview

- `place_test_order.py` - Place one test order to verify setup
- `dry_run_bot.py` - Simulated trading (no real orders)
- `pacifica_sdk.py` - SDK integration for signing orders
- `config.py` - Bot configuration
- `.env` - Your private keys (NOT committed to git)

## Security Notes

⚠️ Your `.env` file contains sensitive keys
⚠️ Never commit `.env` to git (it's in `.gitignore`)
⚠️ Consider using a separate trading wallet with limited funds
⚠️ The private key in `.env` can control your wallet
