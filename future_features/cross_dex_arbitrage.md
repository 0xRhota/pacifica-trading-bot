# Cross-DEX Spread Arbitrage Research

## Strategy Overview

**Concept**: Monitor price spreads between perpetual DEXs (Lighter, Extended, Paradex), then:
- **LONG** on cheaper exchange
- **SHORT** on expensive exchange
- Wait for spread convergence (typically reverts to 0-2 bps)
- **Delta neutral** = no directional exposure, pure spread profit
- Bonus: Farm points on both platforms while arbitraging

## Exchanges Analyzed

### 1. Lighter (zkSync) - ALREADY INTEGRATED
- **Status**: ✅ Full SDK working
- **Base URL**: `https://mainnet.zklighter.elliot.ai`
- **Fees**: ZERO (0%)
- **SDK**: `lighter` Python package
- **Our Account**: Index 341823, API Key Index 2
- **Markets**: 101+ pairs (BTC, ETH, SOL, etc.)

**Key Endpoints**:
```python
# Get prices
GET /api/v1/orderBooks  # All markets with bid/ask
GET /api/v1/orderBook/{market_id}  # Single market

# Place orders (via SDK)
signer_client.create_market_order(symbol, is_buy, amount)
```

### 2. Extended (Starknet) - NEW INTEGRATION NEEDED
- **Status**: ⚠️ Requires setup
- **Base URL**: `https://api.starknet.extended.exchange/api/v1`
- **Testnet**: `https://api.starknet.sepolia.extended.exchange/api/v1`
- **Fees**: ~0.025% maker/taker (need to verify)
- **SDK**: `x10xchange/python_sdk` (GitHub)
- **Authentication**: API Key + Stark Key signatures (SNIP12)
- **Markets**: BTC-USD, ETH-USD, SOL-USD, etc.

**Key Endpoints**:
```python
# Get prices
GET /api/v1/info/markets/{market}/orderbook
# Response: {"market": "BTC-USD", "bid": [{"qty": "0.04852", "price": "61827.7"}], ...}

GET /api/v1/info/markets/{market}/stats  # Mark price, funding, volume

# Place orders
POST /api/v1/user/order
# Requires: market, side, qty, price, fee, settlement (Stark signature)

# Get positions
GET /api/v1/user/positions?market={market}
```

**Requirements to Trade**:
1. Account on Extended.exchange UI
2. API key from account management page
3. Starknet wallet (for Stark Key signatures)
4. Python SDK with Rust components for signing

### 3. Paradex (Starknet) - NEW INTEGRATION NEEDED
- **Status**: ⚠️ Requires setup
- **Base URL**: `https://api.prod.paradex.trade/v1` (mainnet)
- **Testnet**: `https://api.testnet.paradex.trade/v1`
- **Fees**: ZERO (0%)
- **SDK**: `paradex-py` Python package
- **Authentication**: L1 wallet + JWT generation
- **Markets**: BTC-USD-PERP, ETH-USD-PERP, SOL-USD-PERP, etc.

**Key Endpoints (via SDK)**:
```python
from paradex_py import Paradex
from paradex_py.environment import Environment

paradex = Paradex(
    env=Environment.MAINNET,
    l1_address="0x...",
    l1_private_key="0x..."
)

# Get prices
bbo = await paradex.api_client.fetch_bbo(market="BTC-USD-PERP")
markets = await paradex.api_client.fetch_markets()

# Place orders
from paradex_py.orders import Order
order = Order(market="BTC-USD-PERP", side="BUY", size=1.0, price=50000.0)
result = await paradex.api_client.submit_order(order)

# Get positions
positions = await paradex.api_client.fetch_positions()
```

**Requirements to Trade**:
1. Ethereum wallet (L1)
2. paradex-py SDK installed
3. Onboarding via SDK (auto-handled with auto_auth=True)

## Implementation Architecture

### Phase 1: Spread Monitor (READ-ONLY)
Build a service that monitors spreads without trading:

```
spread_monitor/
├── __init__.py
├── config.py              # API configs for all DEXs
├── fetchers/
│   ├── lighter_fetcher.py # ✅ Already have
│   ├── extended_fetcher.py # New - fetch orderbook
│   └── paradex_fetcher.py # New - fetch BBO
├── spread_calculator.py   # Calculate cross-DEX spreads
└── alert_service.py       # Alert when spread > threshold
```

**Spread Calculation**:
```python
# Example: BTC spread between Lighter and Extended
lighter_bid = 61827.0  # Best bid on Lighter
extended_ask = 61820.0  # Best ask on Extended

spread_bps = ((lighter_bid - extended_ask) / extended_ask) * 10000
# If spread_bps > 5 (5 bps), potential arb opportunity
```

### Phase 2: Execution Engine (TRADING)
Add execution after monitoring proves the opportunity:

```
spread_arbitrage/
├── monitor/               # From Phase 1
├── executor/
│   ├── lighter_executor.py  # ✅ Already have
│   ├── extended_executor.py # New
│   └── paradex_executor.py  # New
├── position_manager.py    # Track net exposure, collateral
└── risk_manager.py        # Stop losses, max position sizes
```

## Key Risks & Challenges

### 1. Execution Risk
- Spreads can disappear before both legs execute
- Solution: Use limit orders, execute fast, atomic if possible

### 2. Collateral Management
- PnL on one exchange doesn't offset the other
- Need to periodically rebalance collateral between DEXs
- May need to close profitable leg to move funds

### 3. Liquidation Risk
- If spread blows out, one leg could get liquidated
- Use low leverage (2-3x max)
- Set wide liquidation margins

### 4. Fee Differences
- Lighter: 0% fees
- Paradex: 0% fees
- Extended: ~0.025% fees
- Must account for fees in profitability calculation

### 5. Different Funding Rates
- Each DEX has different funding rates
- Could add/subtract from spread profit
- Opportunity: Fund rate arb on top of spread arb

### 6. Authentication Complexity
- Lighter: Simple API key + account index
- Extended: Stark Key signatures (complex)
- Paradex: Ethereum wallet + JWT

## Feasibility Assessment

| Factor | Lighter | Extended | Paradex |
|--------|---------|----------|---------|
| API Complexity | ✅ Easy | ⚠️ Medium (Stark sigs) | ✅ Easy |
| SDK Available | ✅ Yes | ✅ Yes | ✅ Yes |
| Zero Fees | ✅ Yes | ❌ No (~0.025%) | ✅ Yes |
| Account Needed | ✅ Have | ⚠️ Need | ⚠️ Need |
| Wallet Required | No | Starknet | Ethereum |

### Recommended Approach

**Option A: Lighter + Paradex** (Easiest)
- Both have zero fees
- Both have easy Python SDKs
- Both use async/await patterns
- Only need Ethereum wallet for Paradex

**Option B: Lighter + Extended** (More Complex)
- Extended has small fees (reduces profitability)
- Stark Key signatures add complexity
- But might have wider spreads (more opportunity?)

## Estimated Development Effort

### Phase 1: Spread Monitor (Research/Testing)
1. Set up Paradex account & SDK - 1 session
2. Build multi-DEX price fetcher - 1 session
3. Run spread analysis for 1 week - monitor only
4. Document spread patterns & opportunities

### Phase 2: Trading Execution
1. Add Paradex executor - 1 session
2. Build position manager - 1 session
3. Test on testnet - 1-2 sessions
4. Deploy to mainnet with small size

## Quick Start Commands

```bash
# Install Paradex SDK
pip install paradex-py

# Install Extended SDK (if choosing that route)
pip install git+https://github.com/x10xchange/python_sdk.git
```

## Next Steps

1. **Decision**: Choose Lighter+Paradex or Lighter+Extended
2. **Accounts**: Set up account(s) on chosen DEX
3. **Phase 1**: Build spread monitor
4. **Analysis**: Run for 1 week, analyze spread patterns
5. **Phase 2**: Add execution if spreads are profitable

## References

- Extended API Docs: https://api.docs.extended.exchange/
- Extended Python SDK: https://github.com/x10xchange/python_sdk
- Paradex Docs: https://docs.paradex.trade
- Paradex Python SDK: https://tradeparadex.github.io/paradex-py/
- Lighter API: https://apidocs.lighter.xyz
