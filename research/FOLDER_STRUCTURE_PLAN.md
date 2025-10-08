# Multi-DEX Folder Structure Plan

## Proposed New Structure

```
pacifica-trading-bot/
│
├── bot/                          # Core trading engine (DEX-agnostic)
│   ├── __init__.py
│   ├── engine.py                 # Main TradingEngine class
│   ├── config.py                 # Unified BotConfig
│   └── launcher.py               # Bot startup script
│
├── dexes/                        # DEX-specific implementations
│   ├── __init__.py
│   ├── base.py                   # Abstract DEXAdapter interface
│   │
│   ├── pacifica/                 # Pacifica DEX adapter
│   │   ├── __init__.py
│   │   ├── adapter.py            # PacificaAdapter(DEXAdapter)
│   │   ├── sdk.py                # Current pacifica_sdk.py → renamed
│   │   └── api.py                # Current pacifica_bot.py → renamed
│   │
│   └── lighter/                  # Lighter DEX adapter
│       ├── __init__.py
│       ├── adapter.py            # LighterAdapter(DEXAdapter)
│       └── client.py             # Wrapper for lighter-python SDK
│
├── strategies/                   # Trading strategies (DEX-agnostic)
│   ├── __init__.py
│   ├── base.py                   # Abstract Strategy interface
│   └── basic_long.py             # Current strategy from strategies.py
│
├── utils/                        # Shared utilities
│   ├── __init__.py
│   ├── risk_manager.py           # Current risk_manager.py → moved here
│   ├── trade_tracker.py          # Current trade_tracker.py → moved here
│   └── logger.py                 # Logging utilities
│
├── scripts/                      # Helper scripts
│   ├── view_trades.py            # Keep as-is
│   ├── place_order_now.py        # Keep as-is
│   ├── sync_tracker.py           # Keep as-is
│   └── test_dex.py               # New: Test individual DEX connection
│
├── archive/                      # Old code (keep for reference)
│   └── ... (existing archive files)
│
├── research/                     # Documentation and research
│   ├── cambrian/                 # Cambrian research
│   ├── lighter/                  # Lighter research
│   │   └── LIGHTER_REQUIREMENTS.md
│   ├── MULTI_DEX_ARCHITECTURE.md
│   └── FOLDER_STRUCTURE_PLAN.md  # This file
│
├── .env                          # All private keys
├── config.yaml                   # NEW: Multi-DEX configuration
├── live_bot.py                   # DEPRECATED → use bot/launcher.py
├── README.md
└── requirements.txt              # Python dependencies
```

## Migration Plan

### Phase 1: Create New Folders (No Code Changes)
```bash
mkdir -p bot
mkdir -p dexes/pacifica
mkdir -p dexes/lighter
mkdir -p strategies
mkdir -p utils
```

### Phase 2: Move Files (One at a Time, Test After Each)

#### Step 1: Move Utilities
```bash
# Test that imports still work after each move
mv risk_manager.py utils/risk_manager.py
mv trade_tracker.py utils/trade_tracker.py
# Update imports in dependent files
```

#### Step 2: Move Pacifica Code
```bash
mv pacifica_sdk.py dexes/pacifica/sdk.py
mv pacifica_bot.py dexes/pacifica/api.py
# Create dexes/pacifica/adapter.py (new file)
```

#### Step 3: Move Strategy Code
```bash
mv strategies.py strategies/basic_long.py
# Create strategies/base.py (new file)
```

#### Step 4: Create Core Bot
```bash
# Extract trading logic from live_bot.py → bot/engine.py
# Create bot/config.py (merge config.py into it)
# Create bot/launcher.py (new main entry point)
```

### Phase 3: Create Lighter Integration
```bash
# Install lighter-python
pip install git+https://github.com/elliottech/lighter-python.git

# Create new files
touch dexes/lighter/adapter.py
touch dexes/lighter/client.py
```

### Phase 4: Create Abstractions
```bash
touch dexes/base.py           # DEXAdapter interface
touch strategies/base.py      # Strategy interface
touch bot/engine.py          # TradingEngine class
```

## File Contents Preview

### `dexes/base.py` - DEXAdapter Interface
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class DEXAdapter(ABC):
    """Abstract interface for all DEX integrations"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection to DEX"""
        pass

    @abstractmethod
    async def get_price(self, symbol: str) -> float:
        """Get current market price"""
        pass

    @abstractmethod
    async def get_balance(self) -> Dict:
        """Get account balance and equity"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        pass

    @abstractmethod
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        size_usd: float
    ) -> Dict:
        """Place market order"""
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> Dict:
        """Close existing position"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """DEX name (e.g., 'pacifica', 'lighter')"""
        pass
```

### `bot/engine.py` - Trading Engine
```python
import asyncio
from typing import List
from dexes.base import DEXAdapter
from strategies.base import Strategy
from utils.risk_manager import RiskManager
from utils.trade_tracker import TradeTracker

class TradingEngine:
    """Core trading engine that works across multiple DEXes"""

    def __init__(
        self,
        dex_adapters: List[DEXAdapter],
        strategy: Strategy,
        config: dict
    ):
        self.dexes = dex_adapters
        self.strategy = strategy
        self.config = config
        self.risk_manager = RiskManager()
        self.tracker = TradeTracker()

    async def run(self):
        """Main bot loop"""
        while True:
            for dex in self.dexes:
                await self._trade_cycle(dex)
            await asyncio.sleep(self.config['check_frequency'])

    async def _trade_cycle(self, dex: DEXAdapter):
        """One trading cycle on a specific DEX"""
        # Check and manage positions
        positions = await dex.get_positions()
        for pos in positions:
            if self.strategy.should_close(pos):
                await dex.close_position(pos['symbol'])

        # Open new positions
        if self.strategy.should_open_new():
            symbol = self.strategy.pick_symbol()
            size = self.strategy.calculate_size()
            await dex.place_market_order(symbol, 'buy', size)
```

### `config.yaml` - Multi-DEX Configuration
```yaml
# DEX Configurations
dexes:
  pacifica:
    enabled: true
    chain: solana
    position_size_min: 10.0
    position_size_max: 15.0
    symbols:
      - SOL
      - PENGU
      - BTC
      - XPL
      - ASTER

  lighter:
    enabled: true
    chain: zksync
    position_size_min: 10.0
    position_size_max: 15.0
    symbols:
      - BTC
      - ETH
      - SOL

# Trading Strategy
trading:
  longs_only: true
  min_profit_threshold: 0.05   # 5%
  max_loss_threshold: 0.003    # 0.3%
  max_leverage: 5.0
  max_position_hold_time: 1800 # 30 minutes

# Timing
timing:
  check_frequency: 45          # seconds
  trade_frequency: 900         # 15 minutes

# Risk Management
risk:
  max_daily_loss: 200.0
  stop_trading_on_loss: true
```

## Import Path Changes

### Old Imports (Current)
```python
from pacifica_sdk import PacificaSDK
from pacifica_bot import PacificaAPI
from risk_manager import RiskManager
from trade_tracker import tracker
from strategies import Strategy
```

### New Imports (After Refactor)
```python
from dexes.pacifica.adapter import PacificaAdapter
from dexes.lighter.adapter import LighterAdapter
from utils.risk_manager import RiskManager
from utils.trade_tracker import tracker
from strategies.basic_long import BasicLongStrategy
from bot.engine import TradingEngine
```

## Testing Strategy

### After Each Migration Step
```bash
# 1. Run existing bot to ensure it still works
python3 live_bot.py  # Should still work

# 2. Run tests
python3 -m pytest tests/  # If we had tests

# 3. Check imports
python3 -c "from utils.risk_manager import RiskManager; print('OK')"
```

### After Full Refactor
```bash
# Test Pacifica adapter independently
python3 scripts/test_dex.py --dex pacifica

# Test Lighter adapter independently
python3 scripts/test_dex.py --dex lighter

# Test unified bot
python3 bot/launcher.py --dex pacifica
python3 bot/launcher.py --dex lighter
python3 bot/launcher.py --dex all
```

## Rollback Plan

If refactor breaks something:
1. Git stash or revert changes
2. Keep `archive/` folder with working code
3. Migrate one file at a time, test each
4. Use feature branches for major changes

## Benefits of New Structure

1. **Scalability**: Easy to add new DEXes (just implement DEXAdapter)
2. **Testability**: Each component can be tested independently
3. **Maintainability**: Clear separation of concerns
4. **Reusability**: Strategies work on any DEX
5. **Clarity**: Obvious where each piece of code lives

## Next Steps

1. **Get user approval** on this structure
2. **Create folders** (phase 1)
3. **Move one file at a time** (phase 2)
4. **Test after each move**
5. **Don't touch live bot** until refactor is complete and tested
