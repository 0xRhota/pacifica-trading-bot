# Lighter Wallet Security - How It Works

## Your Question Answered

**Q: What ETH private key do I need? Is it my main wallet?**

**A: YES, it's your main Lighter wallet - but you can create a SEPARATE trading sub-account to isolate funds.**

## How Lighter Accounts Work

### 1. Main Wallet (ETH_PRIVATE_KEY)
- This is your Ethereum wallet that you use to log into Lighter
- It's the wallet you deposit funds into
- **You DO need this private key** for initial setup

### 2. Sub-Accounts (Isolated Trading Accounts)
- Lighter allows you to create **multiple sub-accounts** tied to your main wallet
- Each sub-account has its own balance
- **Sub-accounts are financially isolated** - only the funds in that sub-account can be traded

### 3. API Keys (API_KEY_PRIVATE_KEY)
- These are **separate keys** generated just for API trading
- You can have up to 256 API keys per account/sub-account
- API keys CANNOT withdraw funds, only trade

## Security Setup (Recommended)

### Option 1: Use Sub-Account (SAFEST) ✅
```
Your Main Lighter Wallet
├── Main Account (your login wallet - keep most funds here)
├── Sub-Account #1 (for bot trading - deposit $150 here)
│   └── API Key #3 (bot uses this to trade)
└── Sub-Account #2 (for manual trading)
```

**Benefits**:
- Bot only has access to sub-account funds
- Main wallet funds are isolated
- Can't accidentally trade with your whole balance

### Option 2: Use Main Account (LESS SAFE)
```
Your Main Lighter Wallet
└── Main Account (all funds + bot trading here)
    └── API Key #3 (bot uses this)
```

**Risk**: Bot has access to all funds in main account

## What Private Keys You Need

### Setup Phase (One Time)
```bash
# .env
ETH_PRIVATE_KEY=your_main_lighter_wallet_private_key_here
```

You need this to:
1. Query which sub-accounts exist
2. Create new sub-accounts (if needed)
3. Generate API keys for trading

### Bot Runtime (Daily Use)
```bash
# .env
API_KEY_PRIVATE_KEY=generated_trading_key_here
ACCOUNT_INDEX=1  # Sub-account number (0 = main, 1+ = sub-accounts)
API_KEY_INDEX=3
```

The bot uses:
- **API_KEY_PRIVATE_KEY**: For signing trade orders
- **ACCOUNT_INDEX**: Which sub-account to trade on
- **API_KEY_INDEX**: Which API key slot (2-254 available)

## Setup Process

### Step 1: Export Your Main Wallet Key
```bash
# In your Lighter wallet (browser/app)
# Export private key → copy it
ETH_PRIVATE_KEY="0x1234...your_key"
```

⚠️ **Security Note**: This key has access to your main wallet. Never commit it to git.

### Step 2: Create Sub-Account (Optional but Recommended)
```python
# Run once to create isolated trading sub-account
import lighter

client = lighter.Client(ETH_PRIVATE_KEY)
sub_account = await client.create_sub_account()
# Returns: ACCOUNT_INDEX = 1 (or 2, 3, etc.)
```

### Step 3: Generate API Key for Bot
```python
# Run the system_setup.py example
# It generates:
private_key, public_key = lighter.create_api_key()
# Save this private_key as API_KEY_PRIVATE_KEY
```

### Step 4: Fund the Sub-Account
```bash
# In Lighter UI
# Transfer $150 from main account → sub-account #1
# Now bot can only trade with $150
```

### Step 5: Bot Uses API Key Only
```python
# Bot runtime - NO ETH_PRIVATE_KEY needed!
bot = lighter.SignerClient(
    private_key=API_KEY_PRIVATE_KEY,  # Trading key
    account_index=1,                   # Sub-account #1
    api_key_index=3
)
# Bot can only:
# - Trade on sub-account #1
# - Cannot withdraw funds
# - Cannot access other sub-accounts
```

## What Can the API Key Do?

### CAN:
- ✅ Place market/limit orders
- ✅ Cancel orders
- ✅ Query positions
- ✅ Query balance (of that sub-account only)

### CANNOT:
- ❌ Withdraw funds
- ❌ Transfer to other accounts
- ❌ Access other sub-accounts
- ❌ Change wallet settings

## Key Comparison

| Key Type | Purpose | Risk Level | Used For |
|----------|---------|------------|----------|
| **ETH_PRIVATE_KEY** | Main wallet access | HIGH | Setup only |
| **API_KEY_PRIVATE_KEY** | Trading on specific sub-account | LOW | Bot runtime |

## Best Practice for Your Bot

### Initial Setup (Do Once)
1. Export your Lighter wallet private key (ETH_PRIVATE_KEY)
2. Run setup script to:
   - Find/create sub-account
   - Generate API key
3. Transfer trading funds ($150) to sub-account
4. **Delete ETH_PRIVATE_KEY from .env** after setup

### Bot Runtime (.env file)
```bash
# ONLY these keys needed for daily trading:
LIGHTER_API_KEY_PRIVATE_KEY=638995bed741b84f3cd552cac0a00222440acab5d1a67bbe88926979ba4a4de61e133aab4f53696e
LIGHTER_ACCOUNT_INDEX=1
LIGHTER_API_KEY_INDEX=3
```

No main wallet key needed! ✅

## Answer to "I don't want to expose my main wallet"

**You don't have to!**

1. Use ETH_PRIVATE_KEY **once** to set up sub-account + API key
2. Remove ETH_PRIVATE_KEY from .env after setup
3. Bot runs with just API_KEY_PRIVATE_KEY
4. API key can only trade on one sub-account with limited funds

## Lighter vs Other Wallets

**Q: Can I use a different wallet just for Lighter?**

**A: Yes!** Best practice:

1. Create a **new Ethereum wallet** just for Lighter (e.g., in MetaMask)
2. Send only your trading funds ($150) to this new wallet
3. Log into Lighter with this new wallet
4. Export this wallet's private key (it's isolated from your main holdings)
5. Use this as your ETH_PRIVATE_KEY

Now even if compromised:
- Attacker only gets access to Lighter trading funds
- Your main Ethereum wallet is completely separate

## Summary

✅ **ETH_PRIVATE_KEY**: Your Lighter login wallet (use once for setup)
✅ **API_KEY_PRIVATE_KEY**: Generated trading key (what bot uses daily)
✅ **Sub-accounts**: Isolate trading funds from main balance
✅ **Best security**: New wallet just for Lighter → sub-account → API key

The key you sent (`638995bed...`) is an **API_KEY_PRIVATE_KEY**, not your main wallet. This is the SAFE key to use for bot trading! 🔒
