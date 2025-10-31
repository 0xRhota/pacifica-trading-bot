# Multi-DEX Trading Bot Architecture

## Overview
Refactor the Pacifica trading bot to support multiple DEXes (Pacifica + Lighter) with a unified trading engine and DEX-specific adapters.

## Research Summary

### Pacifica DEX (Current)
- **Chain**: Solana
- **Auth**: Ed25519 wallet signatures (Solana keypair)
- **SDK**: Custom `PacificaSDK` class
- **API**: REST API at `https://api.pacifica.fi/api/v1`
- **Order Placement**: JSON payload + Solana signature
- **Key Feature**: Requires sorted JSON keys for signature consistency

### Lighter DEX (New)
- **Chain**: zkSync (Ethereum L2)
- **Auth**: ETH_PRIVATE_KEY + API_KEY_PRIVATE_KEY
- **SDK**: `lighter-python` (pip install from GitHub)
- **API**:
  - Mainnet: `https://mainnet.zklighter.elliot.ai`
  - Testnet: Default in SDK
- **Order Placement**: `SignerClient.create_market_order()`
- **Key Feature**: Async-first SDK, supports up to 253 API keys

## Key Differences

| Feature | Pacifica | Lighter |
|---------|----------|---------|
| Blockchain | Solana | zkSync (ETH L2) |
| Wallet Type | Solana keypair | Ethereum private key |
| SDK Style | Synchronous requests | Async/await |
| Auth Method | Signature headers | API key system |
| Private Key | SOLANA_PRIVATE_KEY | ETH_PRIVATE_KEY + API_KEY_PRIVATE_KEY |

## Proposed Architecture

### Option 1: Single Bot, Multiple DEX Adapters (RECOMMENDED)
```
pacifica-trading-bot/
├── bot/
│   ├── __init__.py
│   ├── engine.py              # Core trading logic (strategy, risk, timing)
│   ├── config.py              # Unified config for all DEXes
│   └── trade_tracker.py       # Unified trade logging
│
├── dexes/
│   ├── __init__.py
│   ├── base.py                # Abstract DEX interface
│   │
│   ├── pacifica/
│   │   ├── __init__.py
│   │   ├── adapter.py         # Implements base DEX interface
│   │   ├── sdk.py             # PacificaSDK
│   │   └── api.py             # PacificaAPI (market data)
│   │
│   └── lighter/
│       ├── __init__.py
│       ├── adapter.py         # Implements base DEX interface
│       └── client.py          # Lighter SDK wrapper
│
├── strategies/
│   ├── __init__.py
│   └── basic_long.py          # Current strategy (can work on any DEX)
│
├── utils/
│   ├── risk_manager.py
│   └── trade_tracker.py
│
├── scripts/
│   └── run_bot.py             # Launches bot on selected DEXes
│
├── .env                       # All private keys
└── config.yaml                # DEX selection, parameters
```

**Pros**:
- Clean separation of concerns
- Easy to add new DEXes
- Shared trading logic across all DEXes
- One bot instance manages all DEXes

**Cons**:
- More upfront refactoring
- Need to handle async vs sync differences

### Option 2: Separate Bots per DEX
```
pacifica-trading-bot/
├── common/
│   ├── strategies.py
│   ├── risk_manager.py
│   └── trade_tracker.py
│
├── pacifica_bot/
│   ├── live_bot.py
│   ├── pacifica_sdk.py
│   └── config.py
│
└── lighter_bot/
    ├── live_bot.py
    ├── lighter_client.py
    └── config.py
```

**Pros**:
- Less refactoring
- Can run independently
- Isolates DEX-specific bugs

**Cons**:
- Code duplication
- Harder to maintain consistency
- Need to run multiple processes

## Recommended Approach: Option 1

### DEX Adapter Interface
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class DEXAdapter(ABC):
    """Abstract interface for DEX integrations"""

    @abstractmethod
    async def get_price(self, symbol: str) -> float:
        """Get current market price"""
        pass

    @abstractmethod
    async def get_balance(self) -> Dict:
        """Get account balance"""
        pass

    @abstractmethod
    async def place_market_order(self, symbol: str, side: str, size: float) -> Dict:
        """Place market order"""
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> Dict:
        """Close position"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get open positions"""
        pass
```

### Unified Bot Engine
```python
class TradingEngine:
    def __init__(self, dex_adapters: List[DEXAdapter], config: BotConfig):
        self.dexes = dex_adapters
        self.config = config
        self.strategy = BasicLongStrategy()
        self.risk_manager = RiskManager()
        self.tracker = TradeTracker()

    async def run(self):
        """Main bot loop - trades on all DEXes"""
        while True:
            for dex in self.dexes:
                await self._trade_on_dex(dex)
            await asyncio.sleep(self.config.CHECK_FREQUENCY_SECONDS)

    async def _trade_on_dex(self, dex: DEXAdapter):
        """Execute trading logic on specific DEX"""
        # Check positions
        positions = await dex.get_positions()

        # Manage existing positions
        for pos in positions:
            if self.should_close(pos):
                await dex.close_position(pos['symbol'])

        # Open new positions
        if self.should_open_new():
            symbol = self.pick_symbol()
            size = self.calculate_size()
            await dex.place_market_order(symbol, 'buy', size)
```

### Configuration
```yaml
# config.yaml
dexes:
  pacifica:
    enabled: true
    chain: solana
    position_size_usd: 10-15
    symbols: [SOL, PENGU, BTC, XPL, ASTER]

  lighter:
    enabled: true
    chain: zksync
    position_size_usd: 10-15
    symbols: [BTC, ETH, SOL]

trading:
  longs_only: true
  min_profit_threshold: 0.05  # 5%
  max_loss_threshold: 0.003   # 0.3%
  check_frequency: 45
  trade_frequency: 900
```

```bash
# .env
# Pacifica
SOLANA_PRIVATE_KEY=your_solana_key_here

# Lighter
ETH_PRIVATE_KEY=your_eth_key_here
LIGHTER_API_KEY_PRIVATE_KEY=your_lighter_api_key_here
```

## Implementation Plan

### Phase 1: Research & Planning (Current)
- [x] Research Lighter API/SDK
- [x] Design architecture
- [ ] Document API differences
- [ ] Create folder structure

### Phase 2: Refactor Existing Code
- [ ] Create `dexes/base.py` with DEXAdapter interface
- [ ] Move Pacifica code to `dexes/pacifica/`
- [ ] Create PacificaAdapter implementing DEXAdapter
- [ ] Extract trading logic to `bot/engine.py`
- [ ] Test Pacifica still works after refactor

### Phase 3: Add Lighter Support
- [ ] Install `lighter-python` SDK
- [ ] Create `dexes/lighter/` folder
- [ ] Implement LighterAdapter
- [ ] Handle async differences (wrap in asyncio if needed)
- [ ] Test on Lighter testnet

### Phase 4: Unified Bot
- [ ] Update config to support multiple DEXes
- [ ] Create unified bot launcher
- [ ] Add DEX-specific trade tracking
- [ ] Test running on both DEXes simultaneously

### Phase 5: Production
- [ ] Add error handling for DEX-specific failures
- [ ] Implement independent position tracking per DEX
- [ ] Add monitoring/logging per DEX
- [ ] Deploy to mainnet

## Challenges to Solve

### 1. Async vs Sync
- Pacifica SDK is synchronous (requests)
- Lighter SDK is async (asyncio)
- **Solution**: Make everything async, wrap Pacifica calls in `asyncio.to_thread()`

### 2. Different Chain Types
- Solana uses different address format than Ethereum
- **Solution**: Store chain-specific addresses in config

### 3. Symbol Differences
- DEXes may have different symbols for same asset
- **Solution**: Symbol mapping in adapter config

### 4. Account Balance Tracking
- Need to track balance separately per DEX
- **Solution**: Each adapter manages its own balance state

### 5. Lot Size Differences
- Different minimum order sizes per DEX
- **Solution**: DEX-specific lot size validation in adapter

## Next Steps

1. **Create folder structure** (don't move code yet)
2. **Document Lighter API requirements** in detail
3. **Write DEXAdapter interface** with all needed methods
4. **Get user approval** on architecture before refactoring

## Notes

- Keep existing Pacifica bot running during refactor
- Use feature branches for new DEX integrations
- Test each DEX independently before combining
- Consider starting with Lighter testnet before mainnet
