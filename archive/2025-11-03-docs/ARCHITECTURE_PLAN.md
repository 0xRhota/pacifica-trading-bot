# Multi-DEX Bot Architecture Plan

**Date**: 2025-11-03  
**Status**: 📋 PLANNING  
**Goal**: Shared core system + per-DEX bot instances

---

## 🎯 Problem Statement

**Requirements**:
1. Multiple bots run separately (one per DEX: Pacifica, Lighter, future DEXs)
2. All bots share the same core system (LLM engine, prompt system, data pipeline)
3. Changes to core system affect all bots easily
4. Each bot can be configured/tested independently
5. Easy to add new DEXs

---

## 🏗️ Proposed Architecture

### Current Structure (Before)
```
llm_agent/                    # Pacifica bot (hardcoded)
├── bot_llm.py               # Entry point
├── llm/                     # LLM decision engine
├── execution/               # Trade execution
├── data/                    # Data pipeline
└── (all hardcoded to Pacifica)
```

### New Structure (After)
```
llm_agent/
├── core/                    # 🔄 SHARED CORE SYSTEM
│   ├── __init__.py
│   ├── trading_engine.py    # LLM decision making (shared)
│   ├── prompt_formatter.py  # Prompt system (shared)
│   ├── data_aggregator.py   # Data pipeline (shared, DEX-agnostic)
│   ├── model_client.py      # LLM client (shared)
│   └── response_parser.py   # Response parsing (shared)
│
├── execution/               # 🔄 SHARED EXECUTION LAYER
│   ├── __init__.py
│   ├── base_executor.py     # Abstract base class
│   └── trade_executor.py    # Implementation (uses DEX adapter)
│
├── bots/                    # 📦 BOT INSTANCES (Per-DEX)
│   ├── __init__.py
│   ├── pacifica_bot.py      # Pacifica bot instance
│   ├── lighter_bot.py      # Lighter bot instance (TO BE CREATED)
│   └── base_bot.py          # Base bot class (shared)
│
└── adapters/                # 🔌 DEX-SPECIFIC ADAPTERS (or use dexes/)
    ├── __init__.py
    ├── pacifica_adapter.py  # Wraps PacificaSDK
    ├── lighter_adapter.py   # Wraps Lighter SDK
    └── base_adapter.py      # Abstract adapter interface

dexes/
├── pacifica/                # DEX SDKs (unchanged)
│   └── pacifica_sdk.py
└── lighter/
    └── lighter_sdk.py
```

---

## 🔄 Core System (Shared)

### `llm_agent/core/trading_engine.py`
- **Purpose**: LLM decision-making logic
- **Dependencies**: None on specific DEX
- **Uses**: `model_client.py`, `prompt_formatter.py`, `data_aggregator.py`
- **Key Methods**:
  - `get_trading_decision(market_data, context)` → Returns trading decisions (DEX-agnostic)
  - `analyze_markets(market_data)` → Technical analysis (DEX-agnostic)

### `llm_agent/core/prompt_formatter.py`
- **Purpose**: Format prompts for LLM
- **Dependencies**: None on specific DEX
- **Uses**: Market data (generic format)
- **Key Methods**:
  - `format_trading_prompt(market_data, context)` → Returns formatted prompt

### `llm_agent/core/data_aggregator.py`
- **Purpose**: Fetch and aggregate market data
- **Dependencies**: Uses DEX adapter (via dependency injection)
- **Key Methods**:
  - `fetch_market_data(adapter)` → Returns generic market data structure
  - `fetch_all_markets(adapter)` → Returns all markets (DEX-agnostic)

### `llm_agent/core/model_client.py`
- **Purpose**: LLM API client
- **Dependencies**: None on specific DEX
- **Unchanged**: Already DEX-agnostic ✅

---

## 🔌 DEX Adapters (Per-DEX)

### `llm_agent/adapters/base_adapter.py`
```python
from abc import ABC, abstractmethod

class BaseDEXAdapter(ABC):
    """Abstract interface for DEX adapters"""
    
    @abstractmethod
    def get_markets(self) -> List[Dict]:
        """Get all available markets"""
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str) -> Dict:
        """Get market data for a symbol"""
        pass
    
    @abstractmethod
    def get_account_balance(self) -> Dict:
        """Get account balance"""
        pass
    
    @abstractmethod
    def place_order(self, order: Dict) -> Dict:
        """Place an order"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        pass
```

### `llm_agent/adapters/pacifica_adapter.py`
- **Purpose**: Wraps `PacificaSDK` to match `BaseDEXAdapter` interface
- **Implementation**: Delegates to `dexes/pacifica/pacifica_sdk.py`
- **Converts**: Pacifica-specific responses to generic format

### `llm_agent/adapters/lighter_adapter.py`
- **Purpose**: Wraps `LighterSDK` to match `BaseDEXAdapter` interface
- **Implementation**: Delegates to `dexes/lighter/lighter_sdk.py`
- **Converts**: Lighter-specific responses to generic format

---

## 📦 Bot Instances (Per-DEX)

### `llm_agent/bots/base_bot.py`
```python
from llm_agent.core.trading_engine import TradingEngine
from llm_agent.core.data_aggregator import DataAggregator
from llm_agent.execution.trade_executor import TradeExecutor
from llm_agent.adapters.base_adapter import BaseDEXAdapter

class BaseBot:
    """Base bot class - shared functionality"""
    
    def __init__(self, dex_adapter: BaseDEXAdapter, config: Dict):
        self.adapter = dex_adapter
        self.config = config
        self.trading_engine = TradingEngine()
        self.data_aggregator = DataAggregator()
        self.trade_executor = TradeExecutor(adapter)
        
    def run_once(self):
        # 1. Fetch market data (uses adapter)
        market_data = self.data_aggregator.fetch_market_data(self.adapter)
        
        # 2. Get trading decisions (shared core)
        decisions = self.trading_engine.get_trading_decision(market_data, context)
        
        # 3. Execute trades (uses adapter)
        self.trade_executor.execute_decisions(decisions)
```

### `llm_agent/bots/pacifica_bot.py`
```python
from llm_agent.bots.base_bot import BaseBot
from llm_agent.adapters.pacifica_adapter import PacificaAdapter
from dexes.pacifica.pacifica_sdk import PacificaSDK

class PacificaBot(BaseBot):
    """Pacifica bot instance"""
    
    def __init__(self, config: Dict):
        # Initialize Pacifica SDK
        sdk = PacificaSDK(...)
        
        # Wrap in adapter
        adapter = PacificaAdapter(sdk)
        
        # Initialize base bot
        super().__init__(adapter, config)
        
    def run(self):
        """Main bot loop"""
        while True:
            self.run_once()
            time.sleep(self.config['interval'])

if __name__ == "__main__":
    bot = PacificaBot(config)
    bot.run()
```

### `llm_agent/bots/lighter_bot.py`
```python
from llm_agent.bots.base_bot import BaseBot
from llm_agent.adapters.lighter_adapter import LighterAdapter
from dexes.lighter.lighter_sdk import LighterSDK

class LighterBot(BaseBot):
    """Lighter bot instance"""
    
    def __init__(self, config: Dict):
        # Initialize Lighter SDK
        sdk = LighterSDK(...)
        
        # Wrap in adapter
        adapter = LighterAdapter(sdk)
        
        # Initialize base bot
        super().__init__(adapter, config)
        
    def run(self):
        """Main bot loop"""
        while True:
            self.run_once()
            time.sleep(self.config['interval'])

if __name__ == "__main__":
    bot = LighterBot(config)
    bot.run()
```

---

## 📁 File Structure After Refactor

```
llm_agent/
├── core/                           # 🔄 SHARED CORE
│   ├── __init__.py
│   ├── trading_engine.py              # LLM decision engine
│   ├── prompt_formatter.py            # Prompt system
│   ├── data_aggregator.py              # Data pipeline
│   ├── model_client.py                 # LLM client
│   └── response_parser.py              # Response parsing
│
├── execution/                         # 🔄 SHARED EXECUTION
│   ├── __init__.py
│   ├── base_executor.py               # Abstract executor
│   └── trade_executor.py              # Trade execution (uses adapter)
│
├── bots/                              # 📦 BOT INSTANCES
│   ├── __init__.py
│   ├── base_bot.py                    # Base bot class
│   ├── pacifica_bot.py                 # Pacifica bot
│   └── lighter_bot.py                 # Lighter bot (TO BE CREATED)
│
├── adapters/                           # 🔌 DEX ADAPTERS
│   ├── __init__.py
│   ├── base_adapter.py                 # Abstract adapter
│   ├── pacifica_adapter.py             # Pacifica adapter
│   └── lighter_adapter.py              # Lighter adapter (TO BE CREATED)
│
└── config/                             # 📝 PER-BOT CONFIGS
    ├── pacifica_config.py              # Pacifica bot config
    ├── lighter_config.py                # Lighter bot config
    └── base_config.py                   # Base config class

dexes/                                  # DEX SDKs (unchanged)
├── pacifica/
│   └── pacifica_sdk.py
└── lighter/
    └── lighter_sdk.py
```

---

## 🔧 Migration Strategy

### Phase 1: Extract Core (No Breaking Changes)
1. Create `llm_agent/core/` directory
2. Move shared code from `llm_agent/llm/` → `llm_agent/core/`
3. Update imports in `bot_llm.py` (still works)
4. **Test**: Pacifica bot still runs

### Phase 2: Create Adapter Layer
1. Create `llm_agent/adapters/base_adapter.py`
2. Create `llm_agent/adapters/pacifica_adapter.py`
3. Wrap `PacificaSDK` in adapter
4. Update `data_aggregator.py` to use adapter
5. **Test**: Pacifica bot still runs

### Phase 3: Create Bot Base Class
1. Create `llm_agent/bots/base_bot.py`
2. Refactor `bot_llm.py` → `bots/pacifica_bot.py`
3. `bot_llm.py` becomes thin wrapper (backward compatibility)
4. **Test**: Pacifica bot still runs

### Phase 4: Create Lighter Bot
1. Create `llm_agent/adapters/lighter_adapter.py`
2. Create `llm_agent/bots/lighter_bot.py`
3. **Test**: Lighter bot runs independently

### Phase 5: Cleanup
1. Remove old `bot_llm.py` (or keep as wrapper)
2. Update documentation
3. Update scripts/references

---

## ✅ Benefits

1. **Shared Core**: Changes to `core/` affect all bots
2. **Independent Bots**: Each bot can be configured/tested separately
3. **Easy Extension**: Add new DEX = create adapter + bot instance
4. **Clean Separation**: DEX-specific code isolated in adapters
5. **Backward Compatible**: Existing Pacifica bot continues working

---

## 🚨 Considerations

1. **Logging**: Each bot has its own log file (`logs/pacifica_bot.log`, `logs/lighter_bot.log`)
2. **Config**: Per-bot config files or env vars (`PACIFICA_*`, `LIGHTER_*`)
3. **Trade Tracker**: Shared tracker or per-bot tracker? (Recommendation: shared with DEX field)
4. **Data Sources**: Some data sources (Deep42, CoinGecko) are DEX-agnostic → stay in core
5. **Prompts**: Shared prompts or per-DEX prompts? (Recommendation: shared, but allow per-DEX overrides)

---

## 📝 Next Steps

1. **Review this plan** - Does this architecture meet your needs?
2. **Execute Phase 1** - Extract core (no breaking changes)
3. **Test Pacifica bot** - Ensure it still works
4. **Execute Phase 2-4** - Build adapter layer and Lighter bot
5. **Update documentation** - Reflect new architecture

---

**Status**: ⏸️ AWAITING REVIEW


