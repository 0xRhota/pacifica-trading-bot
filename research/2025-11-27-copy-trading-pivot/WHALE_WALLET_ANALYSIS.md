# Hyperliquid Whale Wallet Analysis
## Copy Trading Candidates

**Date**: 2025-11-29
**Status**: Live API Data Collected

---

## Data Sources Available

### FREE APIs (Use These)
| Source | URL | Access |
|--------|-----|--------|
| **Hyperliquid Info API** | `https://api.hyperliquid.xyz/info` | FREE - No API key needed |
| **HyperTracker** | `https://app.coinmarketman.com/hypertracker` | FREE - Web UI |
| **Hyperliquid Leaderboard** | `https://app.hyperliquid.xyz/leaderboard` | FREE - Web UI |

### PAID APIs (Backup)
| Source | URL | Cost |
|--------|-----|------|
| CoinGlass API | `open-api-v4.coinglass.com` | Startup plan $50+/mo |
| Nansen API | `api.nansen.ai` | Enterprise pricing |

---

## Top Whale Analysis (Live Data)

### Wallet 1: 0x5b5d51203a0f9079f8aeb098a6523a13f298c060
**Leaderboard Stats**: $116.5M PnL (30D), 91.82% ROI

**LIVE POSITIONS (as of 2025-11-29)**:
| Coin | Side | Size | Entry | Current Value | Unrealized P/L | Leverage |
|------|------|------|-------|---------------|----------------|----------|
| BTC | SHORT | -10.22 | $89,440 | $928K | -$13.7K | 10x |
| ETH | SHORT | -28,778 | $3,523 | $86M | +$15.4M | 10x |
| SOL | SHORT | -284.85 | $142.87 | $38.7K | +$1.97K | 10x |
| INJ | SHORT | -36,877 | $13.06 | $218.8K | +$262.8K | 3x |
| HYPE | SHORT | -1.3M | $42.00 | $44.9M | +$9.9M | 5x |

**Account Summary**:
- Account Value: **$44.56M**
- Total Position Value: **$133.2M**
- Total Unrealized P/L: **+$25.6M**
- Margin Used: **$17.9M**
- Withdrawable: **$26.7M**

**Trading Style**:
- Heavy SHORT bias across all positions
- Multi-asset diversification (BTC, ETH, SOL, INJ, HYPE)
- Moderate leverage (3-10x)
- VERY active: Closes small pieces frequently (recent ETH fills every few seconds)

**Copy Suitability**: ⭐⭐⭐⭐ GOOD
- Pros: Consistent profitability, diversified, moderate leverage
- Cons: Massive position sizes (need to scale down 99%+)

---

### Wallet 2: 0x5d2f4460ac3514ada79f5d9838916e508ab39bb7
**Leaderboard Stats**: $25.2M PnL (30D), **169.37% ROI** (highest!)

**LIVE POSITIONS (as of 2025-11-29)**:
| Coin | Side | Size | Entry | Current Value | Unrealized P/L | Leverage |
|------|------|------|-------|---------------|----------------|----------|
| BTC | SHORT | -1,102 | $111,499 | $100M | **+$22.8M** | 20x |

**Account Summary**:
- Account Value: **$10.54M**
- Total Position Value: **$100M**
- Total Unrealized P/L: **+$22.8M**
- Margin Used: **$5M**
- ROE on this position: **371.6%**

**Trading Style**:
- **SINGLE ASSET FOCUS** - Only BTC
- HIGH leverage (20x)
- LARGE positions ($100M notional)
- Recent trades: Closing shorts at profit ($6K-$150K per fill)
- Entry at $111,499 = Shorted near the top

**Copy Suitability**: ⭐⭐⭐⭐⭐ EXCELLENT
- Pros: HIGHEST ROI, simple strategy (BTC only), clear conviction
- Cons: Higher leverage risk, single asset concentration
- **BEST FOR COPY TRADING** - Easy to follow, predictable

---

### Wallet 3: 0xb83de012dba672c76a7dbbbf3e459cb59d7d6e36
**Leaderboard Stats**: $42.4M PnL (30D), 86.50% ROI

**LIVE POSITIONS (as of 2025-11-29)**:
| Coin | Side | Size | Entry | Current Value | Unrealized P/L | Leverage |
|------|------|------|-------|---------------|----------------|----------|
| BTC | SHORT | -0.0008 | $112,988 | $72 | +$17.76 | 10x |
| ETH | SHORT | -150.99 | $3,227 | $451K | +$35.9K | 10x |
| SOL | SHORT | -0.31 | $149.11 | $42 | +$4.07 | 10x |
| DOGE | SHORT | -4.0 | $0.28 | $0.59 | +$0.53 | 10x |

**Account Summary**:
- Account Value: **$13.75M**
- Total Position Value: **$25M**
- Total Unrealized P/L: **+$36K+**
- Margin Used: **$4.96M**

**Trading Style**:
- SHORT bias like others
- Multi-asset but smaller positions
- Conservative leverage (10x)
- Tight positions - appears to be scaling out

**Copy Suitability**: ⭐⭐⭐ MODERATE
- Pros: Conservative leverage, diversified
- Cons: Smaller positions = harder to detect entries

---

### Wallet 4: 0x51d99A4022a55CAd07a3c958F0600d8bb0B39921 (@qwatio)
**Leaderboard Stats**: Previously $20M+ profit

**LIVE STATUS**: **EMPTY** - No positions or funds
- Account Value: $0
- No active positions

**Status**: Wallet appears inactive/withdrawn

**Copy Suitability**: ❌ NOT USABLE
- Account is empty
- Funds likely moved to new wallet

---

## Recommended Copy Trading Targets

### Primary Target: 0x5d2f4460ac3514ada79f5d9838916e508ab39bb7
**Why**:
- Highest ROI (169%)
- Simple to follow (BTC only)
- Clear conviction trading
- Currently in massive profitable position (+$22.8M)

### Secondary Target: 0x5b5d51203a0f9079f8aeb098a6523a13f298c060
**Why**:
- Largest account ($44.5M)
- Diversified across assets
- Consistent profitability

### Avoid: @qwatio wallets
**Why**:
- Empty/inactive
- Linked to criminal activity (per ZachXBT investigation)
- Wallets likely abandoned

---

## API Usage for Copy Trading

### Monitor Position Opens
```bash
# Poll every 30 seconds for position changes
curl -s -X POST 'https://api.hyperliquid.xyz/info' \
  -H 'Content-Type: application/json' \
  -d '{"type": "clearinghouseState", "user": "0x5d2f4460ac3514ada79f5d9838916e508ab39bb7"}'
```

### Get Recent Fills (Trade History)
```bash
curl -s -X POST 'https://api.hyperliquid.xyz/info' \
  -H 'Content-Type: application/json' \
  -d '{"type": "userFills", "user": "0x5d2f4460ac3514ada79f5d9838916e508ab39bb7"}'
```

### Get Open Orders (Pending)
```bash
curl -s -X POST 'https://api.hyperliquid.xyz/info' \
  -H 'Content-Type: application/json' \
  -d '{"type": "openOrders", "user": "0x5d2f4460ac3514ada79f5d9838916e508ab39bb7"}'
```

---

## Copy Trading Implementation

### Parameters for Small Account (~$500)
```python
WHALE_WALLET = "0x5d2f4460ac3514ada79f5d9838916e508ab39bb7"
POLL_INTERVAL_SECONDS = 30
POSITION_SIZE_MULTIPLIER = 0.00001  # 0.001% of their size ($100M -> $1000)
MAX_LEVERAGE = 5  # Cap our leverage lower than whale's 20x
STOP_LOSS_PCT = 5.0  # Our own risk management
```

### Logic Flow
1. Poll whale positions every 30s
2. Detect NEW positions (compare to previous state)
3. Open same direction at scaled-down size
4. Monitor whale for closes
5. Close when whale closes (or our SL hits)

---

## Key Observations

### Current Market Sentiment (Based on Whale Positions)
- **ALL top whales are SHORT** on BTC, ETH, SOL
- This suggests institutional/whale consensus is BEARISH
- Entry prices: BTC $89K-$112K, ETH $3,200-$3,500

### Risk Factors
1. **Whale could be wrong** - Even $100M accounts can lose
2. **Timing lag** - By the time we copy, price may have moved
3. **Size mismatch** - Their $100M moves markets, our $500 doesn't
4. **Leverage risk** - 20x leverage = 5% move liquidates

### Advantages
1. **Information edge** - Whales often have insider info
2. **Risk management included** - Their survival proves strategy works
3. **No LLM costs** - Pure API polling, no AI calls
4. **Simple execution** - Just follow the leader

---

*Generated from live Hyperliquid API data on 2025-11-29*
